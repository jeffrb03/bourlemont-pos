from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin, get_current_user
from app.models.models import (
    TransaccionPago, BitacoraAuditoria, Usuario, MetodoPago, Orden
)
from app.schemas.schemas import (
    CambioMetodoPagoRequest, BitacoraLogResponse, TransaccionPagoResponse
)

router = APIRouter(prefix="/auditoria", tags=["Auditoría y Bitácora"])

@router.get("/pagos")
def listar_pagos_auditoria(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista las transacciones de pago con información de orden y mesa para auditoría."""
    pagos = db.query(TransaccionPago).order_by(TransaccionPago.id_pago.desc()).limit(100).all()
    resultado = []
    for p in pagos:
        resultado.append({
            "id_pago": p.id_pago,
            "id_orden": p.id_orden,
            "numero_mesa": p.orden.numero_mesa if p.orden else "N/A",
            "metodo_pago": p.metodo_pago,
            "monto_pagado": p.monto_pagado,
            "propina": p.propina,
            "fecha_transaccion": p.fecha_transaccion,
            "id_usuario_cobro": p.id_usuario_cobro,
            "nombre_usuario": p.usuario_cobro.nombre if p.usuario_cobro else "Desconocido",
            "total_orden": p.orden.total if p.orden else 0.00
        })
    return resultado

@router.post("/cambiar-metodo-pago")
def cambiar_metodo_pago(
    payload: CambioMetodoPagoRequest,
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(get_current_admin)
):
    """
    Permite al Administrador corregir un método de pago erróneo en una orden ya cobrada.
    Exige justificación obligatoria y crea un registro inmutable en la bitácora de auditoría.
    """
    pago = db.query(TransaccionPago).filter(TransaccionPago.id_pago == payload.id_pago).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Transacción de pago no encontrada")
        
    metodo_anterior = pago.metodo_pago
    if metodo_anterior == payload.nuevo_metodo_pago:
        raise HTTPException(status_code=400, detail="El nuevo método de pago es idéntico al actual.")
        
    pago.metodo_pago = payload.nuevo_metodo_pago
    
    # Registro inmutable en bitácora
    log = BitacoraAuditoria(
        id_usuario=admin_user.id_usuario,
        accion="CAMBIO_METODO_PAGO",
        descripcion=(
            f"Modificación en Pago #{pago.id_pago} (Orden #{pago.id_orden}): "
            f"Cambio de {metodo_anterior.value} a {payload.nuevo_metodo_pago.value}. "
            f"Justificación administrativa: '{payload.motivo}'"
        )
    )
    db.add(log)
    db.commit()
    
    return {
        "success": True,
        "mensaje": f"Método de pago de la orden #{pago.id_orden} actualizado de {metodo_anterior.value} a {payload.nuevo_metodo_pago.value}.",
        "id_pago": pago.id_pago,
        "nuevo_metodo_pago": pago.metodo_pago
    }

@router.get("/logs", response_model=List[BitacoraLogResponse])
def listar_logs_auditoria(
    db: Session = Depends(get_db),
    admin_user: Usuario = Depends(get_current_admin)
):
    """Lista el historial de eventos inmutables de la bitácora del sistema."""
    logs = db.query(BitacoraAuditoria).order_by(BitacoraAuditoria.id_log.desc()).limit(150).all()
    resultado = []
    for l in logs:
        resultado.append({
            "id_log": l.id_log,
            "id_usuario": l.id_usuario,
            "nombre_usuario": l.usuario.nombre if l.usuario else "Sistema",
            "accion": l.accion,
            "descripcion": l.descripcion,
            "fecha": l.fecha
        })
    return resultado
