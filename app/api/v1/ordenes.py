from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.models import (
    Orden, DetalleOrden, TransaccionPago, Producto, Usuario,
    EstadoOrden, MetodoPago, FacturaFEL, EstadoFEL
)
from app.schemas.schemas import (
    OrdenCreate, OrdenResponse, DetalleOrdenResponse,
    CobrarOrdenRequest, CobrarResponse, FacturaFELResponse
)
from app.services.escandallo import deducir_inventario_por_orden
from app.services.fel import get_fel_provider
from app.services.printer import generar_ticket_termico

router = APIRouter(prefix="/ordenes", tags=["Órdenes y Comandas"])

def _format_orden_response(orden: Orden) -> dict:
    """Helper para serializar la orden con relaciones cargadas."""
    return {
        "id_orden": orden.id_orden,
        "numero_mesa": orden.numero_mesa,
        "id_usuario_creacion": orden.id_usuario_creacion,
        "nombre_usuario_creacion": orden.usuario_creacion.nombre if orden.usuario_creacion else None,
        "estado": orden.estado,
        "fecha_creacion": orden.fecha_creacion,
        "fecha_cierre": orden.fecha_cierre,
        "total": orden.total,
        "items": [
            {
                "id_detalle": item.id_detalle,
                "id_producto": item.id_producto,
                "nombre_producto": item.producto.nombre if item.producto else f"Producto {item.id_producto}",
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "subtotal": item.subtotal
            }
            for item in orden.items
        ],
        "pagos": [
            {
                "id_pago": p.id_pago,
                "metodo_pago": p.metodo_pago,
                "monto_pagado": p.monto_pagado,
                "propina": p.propina,
                "fecha_transaccion": p.fecha_transaccion,
                "id_usuario_cobro": p.id_usuario_cobro,
                "nombre_usuario": p.usuario_cobro.nombre if p.usuario_cobro else None
            }
            for p in orden.pagos
        ],
        "factura_fel": {
            "id_fel": orden.factura_fel.id_fel,
            "uuid_autorizacion": orden.factura_fel.uuid_autorizacion,
            "serie": orden.factura_fel.serie,
            "numero_dte": orden.factura_fel.numero_dte,
            "fecha_certificacion": orden.factura_fel.fecha_certificacion,
            "nit_receptor": orden.factura_fel.nit_receptor,
            "nombre_receptor": orden.factura_fel.nombre_receptor,
            "estado_certificacion": orden.factura_fel.estado_certificacion
        } if orden.factura_fel else None
    }

@router.post("", response_model=OrdenResponse)
def crear_orden(
    payload: OrdenCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Crea una nueva orden/comanda para mesa o barra."""
    if not payload.items:
        raise HTTPException(status_code=400, detail="La orden debe contener al menos un producto.")
        
    nueva_orden = Orden(
        numero_mesa=payload.numero_mesa,
        id_usuario_creacion=current_user.id_usuario,
        estado=EstadoOrden.ABIERTA,
        fecha_creacion=datetime.now(timezone(timedelta(hours=-6))),
        total=Decimal("0.00")
    )
    db.add(nueva_orden)
    db.flush()
    
    total_acumulado = Decimal("0.00")
    for it in payload.items:
        prod = db.query(Producto).filter(Producto.id_producto == it.id_producto).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Producto con ID {it.id_producto} no encontrado.")
            
        subtotal = prod.precio_venta * it.cantidad
        total_acumulado += subtotal
        
        detalle = DetalleOrden(
            id_orden=nueva_orden.id_orden,
            id_producto=prod.id_producto,
            cantidad=it.cantidad,
            precio_unitario=prod.precio_venta,
            subtotal=subtotal
        )
        db.add(detalle)
        
    nueva_orden.total = total_acumulado
    db.commit()
    db.refresh(nueva_orden)
    return _format_orden_response(nueva_orden)

@router.get("", response_model=List[OrdenResponse])
def listar_ordenes(
    estado: Optional[EstadoOrden] = None,
    db: Session = Depends(get_db)
):
    """Lista órdenes activas o históricas."""
    query = db.query(Orden)
    if estado:
        query = query.filter(Orden.estado == estado)
    ordenes = query.order_by(Orden.id_orden.desc()).limit(100).all()
    return [_format_orden_response(o) for o in ordenes]

@router.get("/{id_orden}", response_model=OrdenResponse)
def obtener_orden(id_orden: int, db: Session = Depends(get_db)):
    """Obtiene los detalles completos de una orden."""
    orden = db.query(Orden).filter(Orden.id_orden == id_orden).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return _format_orden_response(orden)

@router.put("/{id_orden}", response_model=OrdenResponse)
def actualizar_orden(
    id_orden: int,
    payload: OrdenCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza una orden comanda abierta (mesa e items)."""
    orden = db.query(Orden).filter(Orden.id_orden == id_orden).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.estado != EstadoOrden.ABIERTA:
        raise HTTPException(status_code=400, detail=f"No se puede modificar una comanda que no esté abierta (estado: {orden.estado.value})")

    orden.numero_mesa = payload.numero_mesa
    # Borrar items anteriores
    db.query(DetalleOrden).filter(DetalleOrden.id_orden == id_orden).delete(synchronize_session=False)

    total_acumulado = Decimal("0.00")
    for it in payload.items:
        prod = db.query(Producto).filter(Producto.id_producto == it.id_producto).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Producto con ID {it.id_producto} no encontrado.")
            
        subtotal = prod.precio_venta * it.cantidad
        total_acumulado += subtotal
        
        detalle = DetalleOrden(
            id_orden=orden.id_orden,
            id_producto=prod.id_producto,
            cantidad=it.cantidad,
            precio_unitario=prod.precio_venta,
            subtotal=subtotal
        )
        db.add(detalle)

    orden.total = total_acumulado
    db.commit()
    db.refresh(orden)
    return _format_orden_response(orden)

@router.post("/{id_orden}/cobrar", response_model=CobrarResponse)
def cobrar_orden(
    id_orden: int,
    payload: CobrarOrdenRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Algoritmo Atómico de Escandallo y Cobro Transaccional.
    Garantiza consistencia ACID: deducción de inventario por receta, registro de pago y certificación FEL.
    """
    orden = db.query(Orden).filter(Orden.id_orden == id_orden).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
        
    if orden.estado != EstadoOrden.ABIERTA:
        raise HTTPException(status_code=400, detail=f"La orden ya se encuentra {orden.estado.value}")
        
    if payload.monto_pagado < orden.total:
        raise HTTPException(
            status_code=400,
            detail=f"El monto pagado (Q{payload.monto_pagado}) es menor al total de la cuenta (Q{orden.total})"
        )

    # Iniciar bloque transaccional atómico
    try:
        # 1. Deducción matemática de inventario según escandallos
        resultado_escandallo = deducir_inventario_por_orden(db, orden)
        
        # 2. Registrar transacción de pago
        pago = TransaccionPago(
            id_orden=orden.id_orden,
            id_usuario_cobro=current_user.id_usuario,
            metodo_pago=payload.metodo_pago,
            monto_pagado=payload.monto_pagado,
            propina=payload.propina,
            fecha_transaccion=datetime.now(timezone(timedelta(hours=-6)))
        )
        db.add(pago)
        
        # 3. Cerrar y actualizar estado de la orden
        orden.estado = EstadoOrden.PAGADA
        orden.fecha_cierre = datetime.now(timezone(timedelta(hours=-6)))
        db.add(orden)
        db.flush()
        
        # 4. Certificación electrónica FEL (SAT Guatemala)
        fel_provider = get_fel_provider()
        resultado_fel = fel_provider.certificar_factura(
            orden=orden,
            nit_receptor=payload.nit_receptor,
            nombre_receptor=payload.nombre_receptor
        )
        
        factura_fel = FacturaFEL(
            id_orden=orden.id_orden,
            uuid_autorizacion=resultado_fel.uuid_autorizacion,
            serie=resultado_fel.serie,
            numero_dte=resultado_fel.numero_dte,
            fecha_certificacion=resultado_fel.fecha_certificacion,
            nit_receptor=resultado_fel.nit_receptor,
            nombre_receptor=resultado_fel.nombre_receptor,
            estado_certificacion=resultado_fel.estado,
            xml_firmado=resultado_fel.xml_firmado
        )
        db.add(factura_fel)
        db.flush()
        
        # 5. Generar formato térmico ESC/POS
        ticket_texto = generar_ticket_termico(orden, pago, factura_fel)
        
        # Confirmar toda la transacción atómica
        db.commit()
        db.refresh(orden)
        
        return CobrarResponse(
            success=True,
            mensaje=f"Orden #{orden.id_orden} cobrada exitosamente. Inventario actualizado y factura FEL emitida.",
            orden=_format_orden_response(orden),
            factura=FacturaFELResponse.model_validate(factura_fel),
            ticket_termico=ticket_texto,
            alertas_inventario=resultado_escandallo.alertas
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Fallo crítico en transacción de cobro e inventario ({str(e)}). Se aplicó ROLLBACK completo."
        )

@router.post("/{id_orden}/anular")
def anular_orden(
    id_orden: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Anula una comanda abierta."""
    orden = db.query(Orden).filter(Orden.id_orden == id_orden).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.estado != EstadoOrden.ABIERTA:
        raise HTTPException(status_code=400, detail="Solo se pueden anular órdenes abiertas.")
        
    orden.estado = EstadoOrden.ANULADA
    orden.fecha_cierre = datetime.now(timezone(timedelta(hours=-6)))
    db.commit()
    return {"success": True, "mensaje": f"Orden #{id_orden} anulada exitosamente."}

@router.put("/{id_orden}", response_model=OrdenResponse)
def actualizar_orden_abierta(
    id_orden: int,
    payload: OrdenCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza una orden/comanda abierta existente."""
    orden = db.query(Orden).filter(Orden.id_orden == id_orden).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.estado != EstadoOrden.ABIERTA:
        raise HTTPException(status_code=400, detail="Solo se pueden actualizar órdenes con estado ABIERTA.")
    if not payload.items:
        raise HTTPException(status_code=400, detail="La orden debe contener al menos un producto.")

    orden.numero_mesa = payload.numero_mesa
    db.query(DetalleOrden).filter(DetalleOrden.id_orden == orden.id_orden).delete()
    
    total_acumulado = Decimal("0.00")
    for it in payload.items:
        prod = db.query(Producto).filter(Producto.id_producto == it.id_producto).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Producto con ID {it.id_producto} no encontrado.")
        subtotal = prod.precio_venta * it.cantidad
        total_acumulado += subtotal
        detalle = DetalleOrden(
            id_orden=orden.id_orden,
            id_producto=prod.id_producto,
            cantidad=it.cantidad,
            precio_unitario=prod.precio_venta,
            subtotal=subtotal
        )
        db.add(detalle)

    orden.total = total_acumulado
    db.commit()
    db.refresh(orden)
    return _format_orden_response(orden)
