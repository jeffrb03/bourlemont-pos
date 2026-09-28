import uuid
from datetime import datetime
from app.models.models import Orden, EstadoFEL
from app.services.fel.base import FacturacionProvider, FacturaResult

class MockFacturacionService(FacturacionProvider):
    """
    Proveedor simulado para pruebas locales offline de alta fidelidad.
    Genera UUIDs válidos y emula la respuesta de la SAT sin consumir folios reales.
    """

    def certificar_factura(self, orden: Orden, nit_receptor: str, nombre_receptor: str) -> FacturaResult:
        auth_uuid = str(uuid.uuid4()).upper()
        serie = "BLM26"
        dte_num = f"{orden.id_orden:09d}"
        now_sat = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-06:00")
        
        xml_simulado = f"""<?xml version="1.0" encoding="UTF-8"?>
<dte:GTDocumento xmlns:dte="http://www.sat.gob.gt/dte/fel/0.2.0" Version="0.1">
  <dte:SAT ClaseDocumento="FACT">
    <dte:DTE ID="DatosEmision">
      <dte:DatosEmision ID="DatosEmisor">
        <dte:DatosGenerales Tipo="FACT" FechaHoraEmision="{now_sat}" CodigoMoneda="GTQ"/>
        <dte:Emisor NITEmisor="98765432" NombreEmisor="BOURLEMONT CHAMPAGNE BAR S.A."/>
        <dte:Receptor IDReceptor="{nit_receptor}" NombreReceptor="{nombre_receptor}"/>
        <dte:Totales>
          <dte:TotalDocumento>{float(orden.total):.2f}</dte:TotalDocumento>
        </dte:Totales>
      </dte:DatosEmision>
      <dte:Certificacion>
        <dte:NumeroAutorizacion Numero="{dte_num}" Serie="{serie}">{auth_uuid}</dte:NumeroAutorizacion>
        <dte:FechaHoraCertificacion>{now_sat}</dte:FechaHoraCertificacion>
      </dte:Certificacion>
    </dte:DTE>
  </dte:SAT>
</dte:GTDocumento>"""

        return FacturaResult(
            uuid_autorizacion=auth_uuid,
            serie=serie,
            numero_dte=dte_num,
            fecha_certificacion=now_sat,
            nit_receptor=nit_receptor or "CF",
            nombre_receptor=nombre_receptor or "CONSUMIDOR FINAL",
            estado=EstadoFEL.CERTIFICADA,
            xml_firmado=xml_simulado
        )

    def anular_factura(self, uuid_autorizacion: str, motivo: str) -> bool:
        return True
