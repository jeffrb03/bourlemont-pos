import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin
from app.models.models import Usuario, RolUsuario
from app.schemas.schemas import (
    UsuarioResponse, UsuarioAdminCreate, UsuarioAdminUpdate
)
from app.core.security import hash_pin, hash_password

router = APIRouter(prefix="/usuarios", tags=["Gestión de Usuarios"])

@router.get("", response_model=List[UsuarioResponse])
def listar_usuarios(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """
    Retorna la lista de todos los colaboradores registrados en el bar.
    Protegido exclusivamente para rol ADMIN.
    Garantiza que NO se expongan hashes de contraseñas ni PINs.
    """
    usuarios = db.query(Usuario).order_by(Usuario.id_usuario.asc()).all()
    return [UsuarioResponse.model_validate(u) for u in usuarios]

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: UsuarioAdminCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """
    Crea un nuevo colaborador (Bartender o Admin).
    - Si rol='BARTENDER': Valida y hashea el PIN de 4 dígitos obligatoriamente.
    - Si rol='ADMIN': Valida y hashea la contraseña obligatoriamente (PIN opcional).
    """
    nombre_limpio = payload.nombre.strip()
    if not nombre_limpio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del colaborador no puede estar vacío."
        )

    existente = db.query(Usuario).filter(Usuario.nombre == nombre_limpio).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un colaborador registrado con el nombre '{nombre_limpio}'."
        )

    pin_hash_val = None
    pass_hash_val = None

    if payload.rol == RolUsuario.BARTENDER:
        if not payload.pin or len(str(payload.pin).strip()) != 4 or not str(payload.pin).strip().isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para el rol BARTENDER es obligatorio ingresar un PIN numérico de 4 dígitos."
            )
        pin_hash_val = hash_pin(str(payload.pin).strip())

    elif payload.rol == RolUsuario.ADMIN:
        if not payload.password or len(payload.password.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Para el rol ADMIN es obligatoria una contraseña de seguridad."
            )
        pass_hash_val = hash_password(payload.password.strip())
        
        # PIN para Admin (si se suministra debe ser de 4 dígitos, si no, se usa fallback "2026")
        if payload.pin and str(payload.pin).strip():
            pin_str = str(payload.pin).strip()
            if len(pin_str) != 4 or not pin_str.isdigit():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El PIN de acceso rápido debe ser de exactamente 4 dígitos numéricos."
                )
            pin_hash_val = hash_pin(pin_str)
        else:
            pin_hash_val = hash_pin("2026")

    nuevo_colaborador = Usuario(
        nombre=nombre_limpio,
        pin_hash=pin_hash_val,
        password_hash=pass_hash_val,
        rol=payload.rol,
        activo=payload.activo,
        foto_url=payload.foto_url
    )

    db.add(nuevo_colaborador)
    db.commit()
    db.refresh(nuevo_colaborador)
    return UsuarioResponse.model_validate(nuevo_colaborador)

@router.put("/{id_usuario}", response_model=UsuarioResponse)
def actualizar_usuario(
    id_usuario: int,
    payload: UsuarioAdminUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """
    Actualiza datos de un colaborador existente.
    Solo modifica y hashea PIN/Password si se envían valores no vacíos.
    """
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colaborador con ID {id_usuario} no encontrado."
        )

    if payload.nombre is not None:
        nombre_limpio = payload.nombre.strip()
        if not nombre_limpio:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre no puede estar vacío.")
        duplicado = db.query(Usuario).filter(Usuario.nombre == nombre_limpio, Usuario.id_usuario != id_usuario).first()
        if duplicado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe otro usuario con el nombre '{nombre_limpio}'."
            )
        usuario.nombre = nombre_limpio

    if payload.rol is not None:
        usuario.rol = payload.rol

    if payload.activo is not None:
        usuario.activo = payload.activo

    # Si se proporciona nuevo PIN
    if payload.pin is not None and str(payload.pin).strip():
        pin_str = str(payload.pin).strip()
        if len(pin_str) != 4 or not pin_str.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El PIN debe ser numérico y contener exactamente 4 dígitos."
            )
        usuario.pin_hash = hash_pin(pin_str)

    # Si se proporciona nueva contraseña
    if payload.password is not None and payload.password.strip():
        pass_str = payload.password.strip()
        if len(pass_str) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 3 caracteres."
            )
        usuario.password_hash = hash_password(pass_str)

    if payload.foto_url is not None:
        usuario.foto_url = payload.foto_url.strip() if payload.foto_url else None

    db.commit()
    db.refresh(usuario)
    return UsuarioResponse.model_validate(usuario)

@router.post("/upload-avatar")
async def upload_avatar_usuario(
    file: UploadFile = File(...),
    admin: Usuario = Depends(get_current_admin)
):
    """
    Carga de imagen para avatar de colaborador. Guarda en frontend/assets/img/.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo seleccionado debe ser una imagen válida."
        )

    original_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
    if original_ext not in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
        original_ext = ".png"

    unique_name = f"avatar_{uuid.uuid4().hex[:12]}{original_ext}"
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

@router.delete("/{id_usuario}")
def desactivar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_current_admin)
):
    """
    Borrado lógico del colaborador (activo = False).
    Preserva integridad referencial en órdenes, pagos y bitácora de auditoría.
    """
    usuario = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Colaborador con ID {id_usuario} no encontrado."
        )

    if usuario.id_usuario == admin.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es posible desactivar la cuenta del administrador actualmente autenticado."
        )

    usuario.activo = False
    db.commit()
    return {
        "success": True,
        "mensaje": f"Colaborador '{usuario.nombre}' desactivado exitosamente (borrado lógico)."
    }
