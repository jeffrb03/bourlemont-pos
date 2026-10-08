from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
import enum

from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, DateTime,
    ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.base import Base

TZ_GUATEMALA = timezone(timedelta(hours=-6))

class RolUsuario(str, enum.Enum):
    ADMIN = "ADMIN"
    BARTENDER = "BARTENDER"

class CategoriaProducto(str, enum.Enum):
    CHAMPAGNE = "CHAMPAGNE"
    LICORES = "LICORES"
    COCTELES_AUTOR = "COCTELES_AUTOR"
    INSUMOS_BASE = "INSUMOS_BASE"

class TipoProducto(str, enum.Enum):
    FINAL = "FINAL"
    INSUMO = "INSUMO"
    COMPUESTO = "COMPUESTO"

class EstadoOrden(str, enum.Enum):
    ABIERTA = "ABIERTA"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"

class MetodoPago(str, enum.Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA_VISA = "TARJETA_VISA"
    TARJETA_MASTERCARD = "TARJETA_MASTERCARD"
    TRANSFERENCIA = "TRANSFERENCIA"

class EstadoArqueo(str, enum.Enum):
    ABIERTO = "ABIERTO"
    CERRADO = "CERRADO"

class EstadoFEL(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    CERTIFICADA = "CERTIFICADA"
    ERROR_OFFLINE = "ERROR_OFFLINE"
    ANULADA = "ANULADA"


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rol: Mapped[RolUsuario] = mapped_column(SQLEnum(RolUsuario), default=RolUsuario.BARTENDER, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    foto_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)

    ordenes_creadas = relationship("Orden", back_populates="usuario_creacion")
    pagos_cobrados = relationship("TransaccionPago", back_populates="usuario_cobro")
    arqueos = relationship("ArqueoCaja", back_populates="usuario")
    logs_auditoria = relationship("BitacoraAuditoria", back_populates="usuario")


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[CategoriaProducto] = mapped_column(SQLEnum(CategoriaProducto), nullable=False)
    tipo: Mapped[TipoProducto] = mapped_column(SQLEnum(TipoProducto), default=TipoProducto.FINAL, nullable=False)
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    stock_ml: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_minimo_ml: Mapped[int] = mapped_column(Integer, default=750, nullable=False)
    unidad_medida: Mapped[str] = mapped_column(String(10), default="ml", nullable=False)
    imagen_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relaciones de escandallos
    recetas_como_final = relationship(
        "RecetaEscandallo",
        foreign_keys="[RecetaEscandallo.id_producto_final]",
        back_populates="producto_final",
        cascade="all, delete-orphan"
    )
    recetas_como_insumo = relationship(
        "RecetaEscandallo",
        foreign_keys="[RecetaEscandallo.id_insumo_base]",
        back_populates="insumo_base"
    )
    detalles_orden = relationship("DetalleOrden", back_populates="producto")


class RecetaEscandallo(Base):
    __tablename__ = "recetas_escandallos"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_receta: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_producto_final: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto", ondelete="CASCADE"), nullable=False)
    id_insumo_base: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"), nullable=False)
    cantidad_descontar_ml: Mapped[int] = mapped_column(Integer, nullable=False)

    producto_final = relationship("Producto", foreign_keys=[id_producto_final], back_populates="recetas_como_final")
    insumo_base = relationship("Producto", foreign_keys=[id_insumo_base], back_populates="recetas_como_insumo")


class Orden(Base):
    __tablename__ = "ordenes"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_orden: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_mesa: Mapped[str] = mapped_column(String(50), nullable=False)
    id_usuario_creacion: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    estado: Mapped[EstadoOrden] = mapped_column(SQLEnum(EstadoOrden), default=EstadoOrden.ABIERTA, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=-6))), nullable=False)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)

    usuario_creacion = relationship("Usuario", back_populates="ordenes_creadas")
    items = relationship("DetalleOrden", back_populates="orden", cascade="all, delete-orphan")
    pagos = relationship("TransaccionPago", back_populates="orden", cascade="all, delete-orphan")
    factura_fel = relationship("FacturaFEL", back_populates="orden", uselist=False, cascade="all, delete-orphan")


class DetalleOrden(Base):
    __tablename__ = "detalle_orden"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_orden: Mapped[int] = mapped_column(Integer, ForeignKey("ordenes.id_orden", ondelete="CASCADE"), nullable=False)
    id_producto: Mapped[int] = mapped_column(Integer, ForeignKey("productos.id_producto"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    orden = relationship("Orden", back_populates="items")
    producto = relationship("Producto", back_populates="detalles_orden")


class TransaccionPago(Base):
    __tablename__ = "transacciones_pago"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_pago: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_orden: Mapped[int] = mapped_column(Integer, ForeignKey("ordenes.id_orden"), nullable=False)
    id_usuario_cobro: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    metodo_pago: Mapped[MetodoPago] = mapped_column(SQLEnum(MetodoPago), nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    propina: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    fecha_transaccion: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=-6))), nullable=False)

    orden = relationship("Orden", back_populates="pagos")
    usuario_cobro = relationship("Usuario", back_populates="pagos_cobrados")


class ArqueoCaja(Base):
    __tablename__ = "arqueos_caja"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_arqueo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=-6))), nullable=False)
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fondo_inicial: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    efectivo_declarado: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    tarjetas_declarado: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    efectivo_teorico_sistema: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    diferencia_efectivo: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    estado: Mapped[EstadoArqueo] = mapped_column(SQLEnum(EstadoArqueo), default=EstadoArqueo.ABIERTO, nullable=False)

    usuario = relationship("Usuario", back_populates="arqueos")


class BitacoraAuditoria(Base):
    __tablename__ = "bitacora_auditoria"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_log: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone(timedelta(hours=-6))), nullable=False)

    usuario = relationship("Usuario", back_populates="logs_auditoria")


class FacturaFEL(Base):
    __tablename__ = "facturas_fel"
    __table_args__ = {"mysql_engine": "InnoDB"}

    id_fel: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_orden: Mapped[int] = mapped_column(Integer, ForeignKey("ordenes.id_orden"), nullable=False, unique=True)
    uuid_autorizacion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    serie: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    numero_dte: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fecha_certificacion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nit_receptor: Mapped[str] = mapped_column(String(20), default="CF", nullable=False)
    nombre_receptor: Mapped[str] = mapped_column(String(150), default="CONSUMIDOR FINAL", nullable=False)
    estado_certificacion: Mapped[EstadoFEL] = mapped_column(SQLEnum(EstadoFEL), default=EstadoFEL.PENDIENTE, nullable=False)
    xml_firmado: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    orden = relationship("Orden", back_populates="factura_fel")
