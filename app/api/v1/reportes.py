from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user
from app.models.models import (
    Orden, EstadoOrden, TransaccionPago, Producto, Usuario, DetalleOrden, CategoriaProducto
)
from app.services.excel_reports import generar_excel_auditoria_ventas

router = APIRouter(prefix="/reportes", tags=["Reportes y Métricas"])

@router.get("/ventas/excel")
def descargar_reporte_excel(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Genera y descarga en memoria el libro de auditoría y proyecciones en .xlsx
    con tres hojas especializadas con paleta Apple Tinted Dark y acentos dorados.
    """
    excel_stream = generar_excel_auditoria_ventas(db)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Bourlemont_Auditoria_Ventas_{timestamp}.xlsx"
    
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    return StreamingResponse(excel_stream, headers=headers)

@router.get("/dashboard")
def obtener_metricas_dashboard(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna métricas clave para el panel gerencial en tiempo real."""
    # Ventas totales
    ventas_pagadas = db.query(Orden).filter(Orden.estado == EstadoOrden.PAGADA).all()
    total_recaudado = sum([float(o.total) for o in ventas_pagadas])
    ordenes_cerradas = len(ventas_pagadas)
    
    # Órdenes abiertas actualmente
    ordenes_abiertas = db.query(Orden).filter(Orden.estado == EstadoOrden.ABIERTA).count()
    
    # Insumos y licores con stock bajo
    productos_bajos = db.query(Producto).filter(Producto.stock_ml <= Producto.stock_minimo_ml).all()
    
    # Ventas por categoría
    ventas_categoria = {"CHAMPAGNE": 0.0, "LICORES": 0.0, "COCTELES_AUTOR": 0.0}
    for ord_obj in ventas_pagadas:
        for item in ord_obj.items:
            cat = item.producto.categoria.value if item.producto else None
            if cat in ventas_categoria:
                ventas_categoria[cat] += float(item.subtotal)
                
    # Bartender con más ventas
    bartenders_metricas = []
    usuarios = db.query(Usuario).all()
    for u in usuarios:
        ords = [o for o in u.ordenes_creadas if o.estado == EstadoOrden.PAGADA]
        tot = sum([float(o.total) for o in ords])
        bartenders_metricas.append({
            "id_usuario": u.id_usuario,
            "nombre": u.nombre,
            "rol": u.rol.value,
            "ordenes_atendidas": len(ords),
            "total_vendido": tot
        })
    bartenders_metricas.sort(key=lambda x: x["total_vendido"], reverse=True)
    
    return {
        "total_recaudado": total_recaudado,
        "ordenes_cerradas": ordenes_cerradas,
        "ordenes_abiertas": ordenes_abiertas,
        "ticket_promedio": (total_recaudado / ordenes_cerradas) if ordenes_cerradas > 0 else 0.0,
        "alertas_stock_critico": len(productos_bajos),
        "productos_stock_critico": [
            {
                "id_producto": p.id_producto,
                "nombre": p.nombre,
                "categoria": p.categoria.value,
                "stock_ml": p.stock_ml,
                "stock_minimo_ml": p.stock_minimo_ml
            }
            for p in productos_bajos
        ],
        "ventas_por_categoria": ventas_categoria,
        "rendimiento_bartenders": bartenders_metricas
    }
