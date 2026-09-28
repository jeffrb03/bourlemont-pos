import logging
import uuid
from datetime import datetime
import httpx
from app.models.models import Orden, EstadoFEL
from app.services.fel.base import FacturacionProvider, FacturaResult
from app.core.config import settings

logger = logging.getLogger("bourlemont.fel.infile")

class InfileFelService(FacturacionProvider):
    """
    Proveedor oficial para SAT Guatemala a través de Infile (FEEL).
    Maneja el flujo de dos pasos:
      1. Firma digital del XML en https://signer-emisores.feel.com.gt/sign_solicitud_firmas/signatures_engine.php
      2. Certificación en https://certificador.feel.com.gt/fel/certificacion/v2/documentos
    Implementa contingencia de caída de red (ERROR_OFFLINE).
    """

    SIGNER_URL = "https://signer-emisores.feel.com.gt/sign_solicitud_firmas/signatures_engine.php"
    CERT_URL = "https://certificador.feel.com.gt/fel/certificacion/v2/documentos"

    def certificar_factura(self, orden: Orden, nit_receptor: str, nombre_receptor: str) -> FacturaResult:
        nit_limpio = (nit_receptor or "CF").strip().upper()
        nombre_limpio = (nombre_receptor or "CONSUMIDOR FINAL").strip()
        now_sat = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-06:00")
        
        # Estructura DTE XML estándar SAT FEL
        xml_dte = f"""<?xml version="1.0" encoding="UTF-8"?>
<dte:GTDocumento xmlns:dte="http://www.sat.gob.gt/dte/fel/0.2.0" Version="0.1">
  <dte:SAT ClaseDocumento="FACT">
    <dte:DTE ID="DatosEmision">
      <dte:DatosEmision ID="DatosEmisor">
        <dte:DatosGenerales Tipo="FACT" FechaHoraEmision="{now_sat}" CodigoMoneda="{settings.DEFAULT_CURRENCY}"/>
        <dte:Emisor NITEmisor="{settings.FEL_NIT_EMITTER.replace('-', '')}" NombreEmisor="BOURLEMONT CHAMPAGNE BAR S.A." CodigoEstablecimiento="1" AfiliacionIVA="GEN"/>
        <dte:Receptor IDReceptor="{nit_limpio}" NombreReceptor="{nombre_limpio}" TipoEspecial="CF" />
        <dte:Frases>
          <dte:Frase CodigoEscenario="1" TipoFrase="1"/>
        </dte:Frases>
        <dte:Items>"""
        
        for idx, item in enumerate(orden.items, 1):
            subtotal = float(item.subtotal)
            base_sin_iva = subtotal / (1 + settings.DEFAULT_TAX_RATE)
            iva_monto = subtotal - base_sin_iva
            prod_name = item.producto.nombre if item.producto else f"Item {item.id_producto}"
            xml_dte += f"""
          <dte:Item NumeroLinea="{idx}" BienOServicio="B">
            <dte:Cantidad>{item.cantidad}</dte:Cantidad>
            <dte:UnidadMedida>UND</dte:UnidadMedida>
            <dte:Descripcion>{prod_name}</dte:Descripcion>
            <dte:PrecioUnitario>{float(item.precio_unitario):.2f}</dte:PrecioUnitario>
            <dte:Precio>{subtotal:.2f}</dte:Precio>
            <dte:Descuento>0.00</dte:Descuento>
            <dte:Impuestos>
              <dte:Impuesto>
                <dte:NombreCorto>IVA</dte:NombreCorto>
                <dte:CodigoUnidadGravable>1</dte:CodigoUnidadGravable>
                <dte:MontoGravable>{base_sin_iva:.2f}</dte:MontoGravable>
                <dte:MontoImpuesto>{iva_monto:.2f}</dte:MontoImpuesto>
              </dte:Impuesto>
            </dte:Impuestos>
            <dte:Total>{subtotal:.2f}</dte:Total>
          </dte:Item>"""

        total_doc = float(orden.total)
        total_iva = total_doc - (total_doc / (1 + settings.DEFAULT_TAX_RATE))
        xml_dte += f"""
        </dte:Items>
        <dte:Totales>
          <dte:TotalImpuestos>
            <dte:TotalImpuesto NombreCorto="IVA" TotalMontoImpuesto="{total_iva:.2f}"/>
          </dte:TotalImpuestos>
          <dte:GranTotal>{total_doc:.2f}</dte:GranTotal>
        </dte:Totales>
      </dte:DatosEmision>
    </dte:DTE>
  </dte:SAT>
</dte:GTDocumento>"""

        headers = {
            "usuario": settings.FEL_USER_PREFIX_WS,
            "llave": settings.FEL_KEY_WS,
            "identificador": f"{settings.FEL_PREFIX_UNIQUE_IDENTIFIER}-{orden.id_orden}-{uuid.uuid4().hex[:6]}"
        }

        try:
            with httpx.Client(timeout=4.0) as client:
                # Paso 1: Firma de documento
                sign_response = client.post(
                    self.SIGNER_URL,
                    data={"xml": xml_dte},
                    headers=headers
                )
                
                if sign_response.status_code != 200:
                    raise Exception(f"Fallo en firma Infile: HTTP {sign_response.status_code} - {sign_response.text}")
                
                signed_xml = sign_response.text
                
                # Paso 2: Certificación del documento firmado
                cert_response = client.post(
                    self.CERT_URL,
                    json={
                        "nit_emisor": settings.FEL_NIT_EMITTER.replace('-', ''),
                        "correo_copia": "",
                        "xml_dte": signed_xml
                    },
                    headers={"Content-Type": "application/json", **headers}
                )
                
                if cert_response.status_code == 200:
                    data = cert_response.json()
                    return FacturaResult(
                        uuid_autorizacion=data.get("uuid"),
                        serie=data.get("serie"),
                        numero_dte=str(data.get("numero")),
                        fecha_certificacion=data.get("fecha"),
                        nit_receptor=nit_limpio,
                        nombre_receptor=nombre_limpio,
                        estado=EstadoFEL.CERTIFICADA,
                        xml_firmado=signed_xml
                    )
                else:
                    raise Exception(f"Fallo en certificación Infile: {cert_response.text}")

        except Exception as e:
            logger.error(f"Error de conexión con servicio FEL Infile ({e}). Activando contingencia ERROR_OFFLINE.")
            # Contingencia SAT: Guardar orden con estado de contingencia offline para reintento automático
            return FacturaResult(
                uuid_autorizacion=None,
                serie="CONTINGENCIA",
                numero_dte=f"OFF-{orden.id_orden}",
                fecha_certificacion=now_sat,
                nit_receptor=nit_limpio,
                nombre_receptor=nombre_limpio,
                estado=EstadoFEL.ERROR_OFFLINE,
                xml_firmado=xml_dte,
                mensaje_error=str(e)
            )

    def anular_factura(self, uuid_autorizacion: str, motivo: str) -> bool:
        logger.info(f"Solicitud de anulación FEL para UUID {uuid_autorizacion} por motivo: {motivo}")
        return True
