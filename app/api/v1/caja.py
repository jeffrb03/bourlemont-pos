from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user
from app.models.models import (
    ArqueoCaja, EstadoArqueo, TransaccionPago, MetodoPago,
    Usuario, RolUsuario, BitacoraAuditoria
)
from app.schemas.schemas import (
    AperturaCajaRequest, CierreCajaRequest, ArqueoResponse
)

router = APIRouter(prefix="/caja", tags=["Caja y Arqueos"])

def _format_arqueo(a: ArqueoCaja, show_theoretical: bool = True) -> dict:
    return {
        "id_arqueo": a.id_arqueo,
        "id_usuario": a.id_usuario,
        "nombre_usuario": a.usuario.nombre if a.usuario else None,
        "fecha_apertura": a.fecha_apertura,
        "fecha_cierre": a.fecha_cierre,
        "fondo_inicial": a.fondo_inicial,
        "efectivo_declarado": a.efectivo_declarado,
        "tarjetas_declarado": a.tarjetas_declarado,
        "efectivo_teorico_sistema": a.efectivo_teorico_sistema if show_theoretical else None,
        "diferencia_efectivo": a.diferencia_efectivo if show_theoretical else None,
        "estado": a.estado
    }

@router.get("/actual")
def obtener_caja_actual(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna el turno de caja abierto actualmente si existe."""
    arqueo_abierto = db.query(ArqueoCaja).filter(ArqueoCaja.estado == EstadoArqueo.ABIERTO).first()
    if not arqueo_abierto:
        return {"abierto": False, "arqueo": None}
        
    is_admin = current_user.rol == RolUsuario.ADMIN
    return {
        "abierto": True,
        "arqueo": _format_arqueo(arqueo_abierto, show_theoretical=is_admin)
    }

@router.post("/apertura", response_model=ArqueoResponse)
def apertura_caja(
    payload: AperturaCajaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Abre un nuevo turno de caja declarando el fondo inicial en efectivo."""
    abierto = db.query(ArqueoCaja).filter(ArqueoCaja.estado == EstadoArqueo.ABIERTO).first()
    if abierto:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un turno de caja abierto (ID #{abierto.id_arqueo}) desde {abierto.fecha_apertura.strftime('%H:%M:%S')}."
        )
        
    nuevo_arqueo = ArqueoCaja(
        id_usuario=current_user.id_usuario,
        fecha_apertura=datetime.now(timezone.utc),
        fondo_inicial=payload.fondo_inicial,
        estado=EstadoArqueo.ABIERTO
    )
    db.add(nuevo_arqueo)
    
    # Log de auditoría
    log = BitacoraAuditoria(
        id_usuario=current_user.id_usuario,
        accion="APERTURA_CAJA",
        descripcion=f"Apertura de turno de caja con fondo inicial de Q{payload.fondo_inicial:.2f}"
    )
    db.add(log)
    
    db.commit()
    db.refresh(nuevo_arqueo)
    return _format_arqueo(nuevo_arqueo, show_theoretical=True)

@router.post("/cierre", response_model=ArqueoResponse)
def cierre_caja_ciego(
    payload: CierreCajaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Arqueo Ciego de Cierre de Turno.
    El bartender declara el conteo físico de billetes y vouchers sin ver el teórico del sistema.
    El sistema calcula el saldo teórico y la diferencia de forma auditada.
    """
    arqueo = db.query(ArqueoCaja).filter(ArqueoCaja.estado == EstadoArqueo.ABIERTO).first()
    if not arqueo:
        raise HTTPException(status_code=400, detail="No hay ningún turno de caja abierto para cerrar.")
        
    fecha_cierre_now = datetime.now(timezone.utc)
    
    # Sumar todas las ventas cobradas en efectivo desde la fecha de apertura
    pagos_efectivo = db.query(
        func.coalesce(func.sum(TransaccionPago.monto_pagado + TransaccionPago.propina), Decimal("0.00"))
    ).filter(
        TransaccionPago.metodo_pago == MetodoPago.EFECTIVO,
        TransaccionPago.fecha_transaccion >= arqueo.fecha_apertura,
        TransaccionPago.fecha_transaccion <= fecha_cierre_now
    ).scalar()
    
    ventas_efectivo = Decimal(str(pagos_efectivo or "0.00"))
    efectivo_teorico = Decimal(str(arqueo.fondo_inicial)) + ventas_efectivo
    diferencia = payload.efectivo_declarado - efectivo_teorico
    
    # Actualizar arqueo
    arqueo.fecha_cierre = fecha_cierre_now
    arqueo.efectivo_declarado = payload.efectivo_declarado
    arqueo.tarjetas_declarado = payload.tarjetas_declarado
    arqueo.efectivo_teorico_sistema = efectivo_teorico
    arqueo.diferencia_efectivo = diferencia
    arqueo.estado = EstadoArqueo.CERRADO
    
    # Registro en bitácora
    log = BitacoraAuditoria(
        id_usuario=current_user.id_usuario,
        accion="CIERRE_CAJA_ARQUEO_CIEGO",
        descripcion=(
            f"Cierre de caja #{arqueo.id_arqueo}. Declarado: Q{payload.efectivo_declarado:.2f} efec, "
            f"Q{payload.tarjetas_declarado:.2f} tarj. Teórico efec: Q{efectivo_teorico:.2f}. "
            f"Diferencia: Q{diferencia:.2f}"
        )
    )
    db.add(log)
    
    db.commit()
    db.refresh(arqueo)
    
    is_admin = current_user.rol == RolUsuario.ADMIN
    return _format_arqueo(arqueo, show_theoretical=is_admin)

@router.get("/historial", response_model=List[ArqueoResponse])
def historial_arqueos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Historial de arqueos y cierres de turno."""
    is_admin = current_user.rol == RolUsuario.ADMIN
    arqueos = db.query(ArqueoCaja).order_by(ArqueoCaja.id_arqueo.desc()).limit(30).all()
    return [_format_arqueo(a, show_theoretical=is_admin) for a in arqueos]
