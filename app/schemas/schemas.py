from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.models import (
    RolUsuario, CategoriaProducto, TipoProducto,
    EstadoOrden, MetodoPago, EstadoArqueo, EstadoFEL
)

# ==================== USUARIOS ====================
class UsuarioBase(BaseModel):
    nombre: str
    rol: RolUsuario
    activo: bool = True
    foto_url: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    password: Optional[str] = None

class UsuarioLoginPin(BaseModel):
    pin: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")

class UsuarioLoginAdmin(BaseModel):
    nombre: str
    password: str

class UsuarioResponse(UsuarioBase):
    id_usuario: int
    fecha_creacion: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class UsuarioAdminCreate(BaseModel):
    nombre: str
    rol: RolUsuario = RolUsuario.BARTENDER
    pin: Optional[str] = None
    password: Optional[str] = None
    activo: bool = True
    foto_url: Optional[str] = None

class UsuarioAdminUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[RolUsuario] = None
    pin: Optional[str] = None
    password: Optional[str] = None
    activo: Optional[bool] = None
    foto_url: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse

# ==================== PRODUCTOS Y RECETAS ====================
class RecetaInsumoItem(BaseModel):
    id_insumo_base: int
    cantidad_descontar_ml: int = Field(..., gt=0)

class RecetaItemResponse(BaseModel):
    id_receta: int
    id_producto_final: int
    id_insumo_base: int
    nombre_insumo: str
    cantidad_descontar_ml: int
    model_config = ConfigDict(from_attributes=True)

class ProductoBase(BaseModel):
    nombre: str
    categoria: CategoriaProducto
    tipo: TipoProducto
    precio_venta: Decimal = Field(default=Decimal("0.00"), ge=0)
    stock_ml: int = Field(default=0)
    stock_minimo_ml: int = Field(default=750, ge=0)
    unidad_medida: str = "ml"
    imagen_url: Optional[str] = None

class ProductoCreate(ProductoBase):
    recetas: Optional[List[RecetaInsumoItem]] = None

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[CategoriaProducto] = None
    tipo: Optional[TipoProducto] = None
    precio_venta: Optional[Decimal] = None
    stock_ml: Optional[int] = None
    stock_minimo_ml: Optional[int] = None
    unidad_medida: Optional[str] = None
    imagen_url: Optional[str] = None

class ProductoResponse(ProductoBase):
    id_producto: int
    botellas_equivalentes: Optional[float] = None
    alerta_stock: Optional[bool] = None
    recetas_como_final: List[RecetaItemResponse] = []
    model_config = ConfigDict(from_attributes=True)

class AsignarRecetaRequest(BaseModel):
    id_producto_final: int
    ingredientes: List[RecetaInsumoItem]

class RecetaUpdate(BaseModel):
    cantidad_descontar_ml: int = Field(..., gt=0)

class RecetaIngredienteCreate(BaseModel):
    id_producto_final: int
    id_insumo_base: int
    cantidad_descontar_ml: int = Field(..., gt=0)

# ==================== ORDENES Y DETALLES ====================
class ItemOrdenCreate(BaseModel):
    id_producto: int
    cantidad: int = Field(..., gt=0)

class OrdenCreate(BaseModel):
    numero_mesa: str = Field(..., min_length=1, max_length=50)
    items: List[ItemOrdenCreate]

class DetalleOrdenResponse(BaseModel):
    id_detalle: int
    id_producto: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    model_config = ConfigDict(from_attributes=True)

class TransaccionPagoResponse(BaseModel):
    id_pago: int
    metodo_pago: MetodoPago
    monto_pagado: Decimal
    propina: Decimal
    fecha_transaccion: datetime
    id_usuario_cobro: int
    nombre_usuario: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class FacturaFELResponse(BaseModel):
    id_fel: int
    uuid_autorizacion: Optional[str] = None
    serie: Optional[str] = None
    numero_dte: Optional[str] = None
    fecha_certificacion: Optional[str] = None
    nit_receptor: str
    nombre_receptor: str
    estado_certificacion: EstadoFEL
    model_config = ConfigDict(from_attributes=True)

class OrdenResponse(BaseModel):
    id_orden: int
    numero_mesa: str
    id_usuario_creacion: int
    nombre_usuario_creacion: Optional[str] = None
    estado: EstadoOrden
    fecha_creacion: datetime
    fecha_cierre: Optional[datetime] = None
    total: Decimal
    items: List[DetalleOrdenResponse] = []
    pagos: List[TransaccionPagoResponse] = []
    factura_fel: Optional[FacturaFELResponse] = None
    model_config = ConfigDict(from_attributes=True)

# ==================== COBRO Y TRANSACCION ====================
class CobrarOrdenRequest(BaseModel):
    metodo_pago: MetodoPago
    monto_pagado: Decimal = Field(..., ge=0)
    propina: Decimal = Field(default=Decimal("0.00"), ge=0)
    nit_receptor: str = "CF"
    nombre_receptor: str = "CONSUMIDOR FINAL"

class CobrarResponse(BaseModel):
    success: bool
    mensaje: str
    orden: OrdenResponse
    factura: Optional[FacturaFELResponse] = None
    ticket_termico: str
    alertas_inventario: List[str] = []

# ==================== CAJA Y ARQUEO ====================
class AperturaCajaRequest(BaseModel):
    fondo_inicial: Decimal = Field(..., ge=0)

class CierreCajaRequest(BaseModel):
    efectivo_declarado: Decimal = Field(..., ge=0)
    tarjetas_declarado: Decimal = Field(..., ge=0)

class ArqueoResponse(BaseModel):
    id_arqueo: int
    id_usuario: int
    nombre_usuario: Optional[str] = None
    fecha_apertura: datetime
    fecha_cierre: Optional[datetime] = None
    fondo_inicial: Decimal
    efectivo_declarado: Optional[Decimal] = None
    tarjetas_declarado: Optional[Decimal] = None
    efectivo_teorico_sistema: Optional[Decimal] = None
    diferencia_efectivo: Optional[Decimal] = None
    estado: EstadoArqueo
    model_config = ConfigDict(from_attributes=True)

# ==================== AUDITORIA ====================
class CambioMetodoPagoRequest(BaseModel):
    id_pago: int
    nuevo_metodo_pago: MetodoPago
    motivo: str = Field(..., min_length=5, max_length=500)

class BitacoraLogResponse(BaseModel):
    id_log: int
    id_usuario: int
    nombre_usuario: Optional[str] = None
    accion: str
    descripcion: str
    fecha: datetime
    model_config = ConfigDict(from_attributes=True)
