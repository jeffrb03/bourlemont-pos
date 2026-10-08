import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.models import (
    Producto, RecetaEscandallo, CategoriaProducto, TipoProducto,
    Usuario, BitacoraAuditoria
)
from app.schemas.schemas import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    RecetaItemResponse, AsignarRecetaRequest, RecetaUpdate, RecetaIngredienteCreate
)

router = APIRouter(prefix="/inventario", tags=["Inventario y Escandallos"])

@router.post("/upload-imagen")
async def upload_imagen_producto(
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Recibe un archivo de imagen, lo almacena en frontend/assets/img/ y retorna la ruta relativa /assets/img/<nombre_archivo>.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo seleccionado debe ser una imagen válida (PNG, JPG, WEBP, SVG)."
        )
    
    original_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
    if original_ext not in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
        original_ext = ".png"
        
    unique_name = f"prod_{uuid.uuid4().hex[:12]}{original_ext}"
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    target_dir = os.path.join(base_dir, "frontend", "assets", "img")
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, unique_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "ok": True,
        "url": f"/assets/img/{unique_name}",
        "filename": unique_name
    }


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
        "imagen_url": p.imagen_url,
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


@router.get("/productos/{id_producto}", response_model=ProductoResponse)
def obtener_producto(id_producto: int, db: Session = Depends(get_db)):
    """Obtiene un producto por ID."""
    prod = db.query(Producto).filter(Producto.id_producto == id_producto).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return _format_producto(prod)


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
        unidad_medida=payload.unidad_medida,
        imagen_url=payload.imagen_url
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

    # Bitácora
    log = BitacoraAuditoria(
        id_usuario=current_user.id_usuario,
        accion="CREAR_PRODUCTO",
        descripcion=f"Producto '{payload.nombre}' (cat: {payload.categoria}) creado por {current_user.nombre}."
    )
    db.add(log)

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
    """Actualiza propiedades, stock o imagen de un producto."""
    prod = db.query(Producto).filter(Producto.id_producto == id_producto).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    cambios = payload.model_dump(exclude_unset=True)
    for k, v in cambios.items():
        setattr(prod, k, v)

    log = BitacoraAuditoria(
        id_usuario=current_user.id_usuario,
        accion="EDITAR_PRODUCTO",
        descripcion=f"Producto #{id_producto} '{prod.nombre}' actualizado por {current_user.nombre}. Cambios: {list(cambios.keys())}"
    )
    db.add(log)

    db.commit()
    db.refresh(prod)
    return _format_producto(prod)


@router.delete("/productos/{id_producto}")
def eliminar_producto(
    id_producto: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Elimina un producto del inventario (borrado físico con confirmación)."""
    prod = db.query(Producto).filter(Producto.id_producto == id_producto).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    nombre_prod = prod.nombre
    # Eliminar recetas asociadas primero
    db.query(RecetaEscandallo).filter(
        RecetaEscandallo.id_producto_final == id_producto
    ).delete()

    db.delete(prod)

    log = BitacoraAuditoria(
        id_usuario=current_user.id_usuario,
        accion="ELIMINAR_PRODUCTO",
        descripcion=f"Producto #{id_producto} '{nombre_prod}' eliminado por {current_user.nombre}."
    )
    db.add(log)

    db.commit()
    return {"success": True, "mensaje": f"Producto '{nombre_prod}' eliminado del inventario."}


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

    # Eliminar recetas previas
    db.query(RecetaEscandallo).filter(
        RecetaEscandallo.id_producto_final == prod_final.id_producto
    ).delete()

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

    prod_final.tipo = TipoProducto.COMPUESTO

    log = BitacoraAuditoria(
        id_usuario=current_user.id_usuario,
        accion="ACTUALIZAR_ESCANDALLO",
        descripcion=f"Escandallo de '{prod_final.nombre}' actualizado: {len(payload.ingredientes)} ingredientes."
    )
    db.add(log)

    db.commit()

    return {
        "success": True,
        "mensaje": f"Escandallo actualizado exitosamente para '{prod_final.nombre}' con {len(payload.ingredientes)} insumos."
    }


@router.delete("/recetas/{id_receta}")
def eliminar_ingrediente_receta(
    id_receta: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Elimina un ingrediente específico de una receta."""
    receta = db.query(RecetaEscandallo).filter(RecetaEscandallo.id_receta == id_receta).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    db.delete(receta)
    db.commit()
    return {"success": True, "mensaje": f"Ingrediente #{id_receta} eliminado de la receta."}


@router.put("/recetas/{id_receta}")
def actualizar_cantidad_receta(
    id_receta: int,
    payload: RecetaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Modifica la deducción en ml de un insumo existente en una receta."""
    receta = db.query(RecetaEscandallo).filter(RecetaEscandallo.id_receta == id_receta).first()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    
    receta.cantidad_descontar_ml = payload.cantidad_descontar_ml
    db.commit()
    return {
        "success": True,
        "mensaje": f"Deducción actualizada a {payload.cantidad_descontar_ml} ml.",
        "id_receta": id_receta,
        "cantidad_descontar_ml": payload.cantidad_descontar_ml
    }


@router.post("/recetas/ingrediente")
def agregar_ingrediente_receta(
    payload: RecetaIngredienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Agrega un insumo base a la receta de un cóctel."""
    prod_final = db.query(Producto).filter(Producto.id_producto == payload.id_producto_final).first()
    if not prod_final:
        raise HTTPException(status_code=404, detail="Producto cóctel no encontrado")
    
    insumo = db.query(Producto).filter(Producto.id_producto == payload.id_insumo_base).first()
    if not insumo:
        raise HTTPException(status_code=404, detail="Insumo base no encontrado")

    existente = db.query(RecetaEscandallo).filter(
        RecetaEscandallo.id_producto_final == payload.id_producto_final,
        RecetaEscandallo.id_insumo_base == payload.id_insumo_base
    ).first()

    if existente:
        existente.cantidad_descontar_ml = payload.cantidad_descontar_ml
    else:
        nueva_receta = RecetaEscandallo(
            id_producto_final=payload.id_producto_final,
            id_insumo_base=payload.id_insumo_base,
            cantidad_descontar_ml=payload.cantidad_descontar_ml
        )
        db.add(nueva_receta)

    prod_final.tipo = TipoProducto.COMPUESTO
    db.commit()
    return {"success": True, "mensaje": f"Insumo '{insumo.nombre}' asignado a '{prod_final.nombre}'."}


@router.get("/recetas")
def listar_todas_las_recetas(db: Session = Depends(get_db)):
    """Lista todos los cócteles y sus recetas detalladas en mililitros."""
    cocteles = db.query(Producto).filter(
        Producto.tipo.in_([TipoProducto.COMPUESTO])
    ).all()

    resultado = []
    for c in cocteles:
        formatted = _format_producto(c)
        resultado.append(formatted)

    return resultado


@router.get("/insumos")
def listar_insumos(db: Session = Depends(get_db)):
    """Lista todos los insumos base disponibles para construir escandallos."""
    insumos = db.query(Producto).filter(
        Producto.tipo == TipoProducto.INSUMO
    ).order_by(Producto.nombre).all()
    return [_format_producto(p) for p in insumos]
