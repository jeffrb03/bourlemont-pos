from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.models import Usuario, RolUsuario
from app.schemas.schemas import (
    UsuarioLoginPin, UsuarioLoginAdmin, UsuarioResponse, TokenResponse
)
from app.core.security import verify_pin, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login-pin", response_model=TokenResponse)
def login_con_pin(payload: UsuarioLoginPin, db: Session = Depends(get_db)):
    """
    Acceso táctil ultra-rápido (< 2 segundos) para Bartenders mediante PIN de 4 dígitos.
    """
    usuarios = db.query(Usuario).filter(Usuario.activo == True).all()
    
    usuario_encontrado = None
    for u in usuarios:
        if verify_pin(payload.pin, u.pin_hash):
            usuario_encontrado = u
            break
            
    if not usuario_encontrado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN incorrecto o usuario inactivo"
        )
        
    token = create_access_token({
        "sub": str(usuario_encontrado.id_usuario),
        "nombre": usuario_encontrado.nombre,
        "rol": usuario_encontrado.rol.value
    })
    
    return TokenResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(usuario_encontrado)
    )

@router.post("/login-admin", response_model=TokenResponse)
def login_administrador(payload: UsuarioLoginAdmin, db: Session = Depends(get_db)):
    """
    Acceso administrativo con contraseña para gerencia y auditoría.
    """
    usuario = db.query(Usuario).filter(
        Usuario.nombre == payload.nombre,
        Usuario.rol == RolUsuario.ADMIN,
        Usuario.activo == True
    ).first()
    
    if not usuario or not usuario.password_hash or not verify_password(payload.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales administrativas inválidas"
        )
        
    token = create_access_token({
        "sub": str(usuario.id_usuario),
        "nombre": usuario.nombre,
        "rol": usuario.rol.value
    })
    
    return TokenResponse(
        access_token=token,
        usuario=UsuarioResponse.model_validate(usuario)
    )

@router.get("/me", response_model=UsuarioResponse)
def obtener_perfil_actual(current_user: Usuario = Depends(get_current_user)):
    """Retorna información del usuario de la sesión activa."""
    return current_user

@router.get("/usuarios", response_model=List[UsuarioResponse])
def listar_usuarios_activos(db: Session = Depends(get_db)):
    """Lista todos los colaboradores activos para selección rápida en barra."""
    return db.query(Usuario).filter(Usuario.activo == True).all()


@router.get("/nit/{nit}")
def buscar_receptor_por_nit(nit: str, current_user: Usuario = Depends(get_current_user)):
    """
    Stub de lookup de NIT en SAT / padrón fiscal local.
    En producción conectar con la API FEL del proveedor certificado (Infile, Fel-Express, etc.).
    Devuelve 404 si no se encuentra → el frontend deja el campo en blanco para ingreso manual.
    """
    from fastapi import HTTPException as _HTTPException

    # CF siempre resuelve como Consumidor Final
    if nit.upper() in ("CF", "C/F"):
        return {"nit": "CF", "nombre": "CONSUMIDOR FINAL"}

    # Padrón local de socios del club (ampliar según base de clientes)
    padron_local: dict = {
        "12345678": "Club Residencial Ciudad Vieja, S.A.",
        "98765432": "Eventos Bourlemont, S.A.",
    }

    if nit in padron_local:
        return {"nit": nit, "nombre": padron_local[nit]}

    raise _HTTPException(
        status_code=404,
        detail=f"NIT {nit!r} no encontrado en padrón local."
    )
