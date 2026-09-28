from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.models import Orden, Producto, RecetaEscandallo, DetalleOrden
from app.core.config import settings

class EscandalloResult:
    def __init__(self):
        self.descuentos_aplicados: List[Dict[str, Any]] = []
        self.alertas: List[str] = []

def deducir_inventario_por_orden(db: Session, orden: Orden) -> EscandalloResult:
    """
    Algoritmo Atómico de Escandallo (Deducción de Inventario en ml).
    Debe ejecutarse DENTRO de una transacción activa (ej. with db.begin(): o antes de commit).
    """
    resultado = EscandalloResult()
    
    # Cargar detalles con productos
    detalles = db.query(DetalleOrden).filter(DetalleOrden.id_orden == orden.id_orden).all()
    
    for item in detalles:
        producto_vendido = db.query(Producto).filter(Producto.id_producto == item.id_producto).first()
        if not producto_vendido:
            continue
            
        # Buscar recetas vinculadas (escandallo)
        recetas = db.query(RecetaEscandallo).filter(
            RecetaEscandallo.id_producto_final == producto_vendido.id_producto
        ).all()
        
        if recetas:
            # Producto compuesto o cóctel con receta en ml
            for r in recetas:
                descuento_ml = item.cantidad * r.cantidad_descontar_ml
                
                # Buscar insumo base
                insumo = db.query(Producto).filter(Producto.id_producto == r.id_insumo_base).with_for_update().first() \
                    if db.bind and db.bind.dialect.name == "mysql" else db.query(Producto).filter(Producto.id_producto == r.id_insumo_base).first()
                
                if insumo:
                    stock_previo = insumo.stock_ml
                    insumo.stock_ml -= descuento_ml
                    db.add(insumo)
                    
                    resultado.descuentos_aplicados.append({
                        "id_producto_final": producto_vendido.id_producto,
                        "producto_final": producto_vendido.nombre,
                        "id_insumo": insumo.id_producto,
                        "insumo": insumo.nombre,
                        "ml_descontados": descuento_ml,
                        "stock_previo": stock_previo,
                        "stock_nuevo": insumo.stock_ml
                    })
                    
                    if insumo.stock_ml < 0:
                        resultado.alertas.append(
                            f"¡ALERTA CRÍTICA! Insumo '{insumo.nombre}' con stock negativo ({insumo.stock_ml} ml)."
                        )
                    elif insumo.stock_ml <= insumo.stock_minimo_ml:
                        resultado.alertas.append(
                            f"Aviso de reposición: '{insumo.nombre}' alcanzó nivel mínimo ({insumo.stock_ml} ml restantes)."
                        )
        else:
            # Producto final simple (ej: copa o botella vendida directamente)
            # Si tiene unidad_medida 'ml' y stock_ml > 0
            if producto_vendido.unidad_medida == "ml" and producto_vendido.stock_ml > 0:
                # Si no hay receta específica, se descuenta 1 porción si está definida o 750ml si es botella
                # Para botellas de champagne directas: 750 ml por unidad vendida
                ml_unidad = 750 if "botella" in producto_vendido.nombre.lower() or producto_vendido.categoria.value == "CHAMPAGNE" else 45
                descuento_ml = item.cantidad * ml_unidad
                
                prod_lock = db.query(Producto).filter(Producto.id_producto == producto_vendido.id_producto).with_for_update().first() \
                    if db.bind and db.bind.dialect.name == "mysql" else db.query(Producto).filter(Producto.id_producto == producto_vendido.id_producto).first()
                
                stock_previo = prod_lock.stock_ml
                prod_lock.stock_ml -= descuento_ml
                db.add(prod_lock)
                
                resultado.descuentos_aplicados.append({
                    "id_producto_final": prod_lock.id_producto,
                    "producto_final": prod_lock.nombre,
                    "id_insumo": prod_lock.id_producto,
                    "insumo": prod_lock.nombre,
                    "ml_descontados": descuento_ml,
                    "stock_previo": stock_previo,
                    "stock_nuevo": prod_lock.stock_ml
                })
                
                if prod_lock.stock_ml <= prod_lock.stock_minimo_ml:
                    resultado.alertas.append(
                        f"Aviso de reposición: '{prod_lock.nombre}' alcanzó nivel mínimo ({prod_lock.stock_ml} ml)."
                    )
                    
    return resultado
