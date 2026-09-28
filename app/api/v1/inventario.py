from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.models import (
    Producto, RecetaEscandallo, CategoriaProducto, TipoProducto,
    Usuario, BitacoraAuditoria
)
from app.schemas.schemas import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    RecetaItemResponse, AsignarRecetaRequest
)

router = APIRouter(prefix="/inventario", tags=["Inventario y Escandallos"])

def _format_producto(p: Producto) -> dict:
    botellas_eq = round(p.stock_ml / 750.0, 2) if p.stock_ml > 0 else 0.0
    alerta = p.stock_ml <= p.stock_minimo_ml
    
    recetas_resp = []
    for r in p.recetas_como_final:
        recetas_resp.append({
            "id_receta": r.id_receta,
            "id_producto_final": r.id_producto_final,
            "id_insumo_base": r.id_insumo_base,
            "nombre_insumo": r.insumo_base.nombre if r.insumo_base else f"Insumo {r.id_insumo_base}",
            "cantidad_descontar_ml": r.cantidad_descontar_ml
        })
        
    return {
        "id_producto": p.id_producto,
        "nombre": p.nombre,
        "categoria": p.categoria,
        "tipo": p.tipo,
        "precio_venta": p.precio_venta,
        "stock_ml": p.stock_ml,
        "stock_minimo_ml": p.stock_minimo_ml,
        "unidad_medida": p.unidad_medida,
        "botellas_equivalentes": botellas_eq,
        "alerta_stock": alerta,
        "recetas_como_final": recetas_resp
    }

@router.get("/productos", response_model=List[ProductoResponse])
def listar_productos(
    categoria: Optional[CategoriaProducto] = None,
    tipo: Optional[TipoProducto] = None,
    db: Session = Depends(get_db)
):
    """Lista todos los productos e insumos con métricas de ml y botellas equivalentes."""
    query = db.query(Producto)
    if categoria:
        query = query.filter(Producto.categoria == categoria)
    if tipo:
        query = query.filter(Producto.tipo == tipo)
    productos = query.order_by(Producto.categoria, Producto.nombre).all()
    return [_format_producto(p) for p in productos]

@router.post("/productos", response_model=ProductoResponse)
def crear_producto(
    payload: ProductoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Crea un nuevo producto o insumo en el inventario."""
    nuevo = Producto(
        nombre=payload.nombre,
        categoria=payload.categoria,
        tipo=payload.tipo,
        precio_venta=payload.precio_venta,
        stock_ml=payload.stock_ml,
        stock_minimo_ml=payload.stock_minimo_ml,
        unidad_medida=payload.unidad_medida
    )
    db.add(nuevo)
    db.flush()
    
    if payload.recetas and payload.tipo in [TipoProducto.COMPUESTO, TipoProducto.FINAL]:
        for r in payload.recetas:
            receta = RecetaEscandallo(
                id_producto_final=nuevo.id_producto,
                id_insumo_base=r.id_insumo_base,
                cantidad_descontar_ml=r.cantidad_descontar_ml
            )
            db.add(receta)
            
    db.commit()
    db.refresh(nuevo)
    return _format_producto(nuevo)

@router.put("/productos/{id_producto}", response_model=ProductoResponse)
def actualizar_producto(
    id_producto: int,
    payload: ProductoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza propiedades o stock de un producto."""
    prod = db.query(Producto).filter(Producto.id_producto == id_producto).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(prod, k, v)
        
    db.commit()
    db.refresh(prod)
    return _format_producto(prod)

@router.post("/recetas")
def asignar_receta_escandallo(
    payload: AsignarRecetaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Asigna o sobrescribe los escandallos (ingredientes en ml) de un cóctel de autor.
    """
    prod_final = db.query(Producto).filter(Producto.id_producto == payload.id_producto_final).first()
    if not prod_final:
        raise HTTPException(status_code=404, detail="Producto final no encontrado")
        
    # Eliminar recetas previas del producto
    db.query(RecetaEscandallo).filter(RecetaEscandallo.id_producto_final == prod_final.id_producto).delete()
    
    for ing in payload.ingredientes:
        insumo = db.query(Producto).filter(Producto.id_producto == ing.id_insumo_base).first()
        if not insumo:
            raise HTTPException(status_code=404, detail=f"Insumo base #{ing.id_insumo_base} no encontrado")
        receta = RecetaEscandallo(
            id_producto_final=prod_final.id_producto,
            id_insumo_base=insumo.id_producto,
            cantidad_descontar_ml=ing.cantidad_descontar_ml
        )
        db.add(receta)
        
    # Asegurar que el producto se marque como compuesto
    prod_final.tipo = TipoProducto.COMPUESTO
    db.commit()
    
    return {
        "success": True,
        "mensaje": f"Escandallo actualizado exitosamente para '{prod_final.nombre}' con {len(payload.ingredientes)} insumos."
    }

@router.get("/recetas")
def listar_todas_las_recetas(db: Session = Depends(get_db)):
    """Lista todos los cócteles y sus recetas detalladas."""
    cocteles = db.query(Producto).filter(
        Producto.categoria.in_([CategoriaProducto.COCTELES_AUTOR, CategoriaProducto.LICORES])
    ).all()
    
    resultado = []
    for c in cocteles:
        if c.recetas_como_final:
            resultado.append(_format_producto(c))
            
    return resultado
