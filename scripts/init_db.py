"""
init_db.py — Inicialización y Poblado de Base de Datos MySQL para Bourlemont POS
==============================================================================
Regenera el esquema relacional en MySQL (XAMPP / InnoDB / utf8mb4) y puebla
los datos semilla iniciales requeridos para la operación del Champagne Bar.

Uso directo:
    python scripts/init_db.py
"""
import sys
import os
import argparse
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Asegurar codificación UTF-8 en salida estándar (Windows console fix)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar path raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.models import (
    Usuario, RolUsuario,
    Producto, CategoriaProducto, TipoProducto,
    RecetaEscandallo,
    Orden, EstadoOrden, DetalleOrden,
    TransaccionPago, MetodoPago,
    ArqueoCaja, EstadoArqueo,
    BitacoraAuditoria,
    FacturaFEL, EstadoFEL
)
from app.core.security import hash_pin, hash_password


def regenerar_tablas():
    """
    Regenera las 9 tablas relacionales con motor InnoDB y charset utf8mb4:
    - usuarios, productos, recetas_escandallos, ordenes, detalle_orden,
      transacciones_pago, arqueos_caja, bitacora_auditoria, facturas_fel.
    """
    print("[*] Conectando a MySQL para regenerar esquema DDL...")
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        Base.metadata.drop_all(bind=engine)
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        conn.commit()
    print("[+] Tablas anteriores eliminadas limpiamente.")

    Base.metadata.create_all(bind=engine)
    print("[+] Esquema DDL recreado exitosamente:")
    for table_name in Base.metadata.tables.keys():
        print(f"    - {table_name}")


def seed_database():
    """
    Inserta los datos semilla iniciales:
    - Bartender: Mateo Morales (PIN: '1234', Rol: 'BARTENDER')
    - Admin: Carlos Bourlemont (PIN: '2026', Password: 'admin', Rol: 'ADMIN')
    - Insumos base: Champagne Brut (750 ml), Gin Tanqueray (750 ml), Cognac Hennessy (700 ml), Jarabe/Sirope (1000 ml).
    - Cócteles: 'Copa Champagne Brut (150 ml)' (Q 260.00), 'French 75 Bourlemont' (Q 185.00), 'Dom Pérignon Vintage' (Q 3,800.00).
    """
    db = SessionLocal()
    try:
        now_gt = datetime.now(timezone(timedelta(hours=-6)))

        # ── 1. USUARIOS ────────────────────────────────────────────────────────
        print("\n[1/5] Insertando usuarios del bar...")
        bartender_mateo = Usuario(
            nombre="Mateo Morales",
            pin_hash=hash_pin("1234"),
            rol=RolUsuario.BARTENDER,
            activo=True
        )
        admin_carlos = Usuario(
            nombre="Carlos Bourlemont",
            pin_hash=hash_pin("2026"),
            password_hash=hash_password("admin"),
            rol=RolUsuario.ADMIN,
            activo=True
        )
        # Bartenders de relevo en barra
        bartender_sofia = Usuario(
            nombre="Sofía Castillo",
            pin_hash=hash_pin("2468"),
            rol=RolUsuario.BARTENDER,
            activo=True
        )
        bartender_alejandro = Usuario(
            nombre="Alejandro Ruiz",
            pin_hash=hash_pin("7788"),
            rol=RolUsuario.BARTENDER,
            activo=True
        )

        db.add_all([bartender_mateo, admin_carlos, bartender_sofia, bartender_alejandro])
        db.flush()
        print(f"    [+] Bartender : Mateo Morales     (PIN: 1234, Rol: BARTENDER)")
        print(f"    [+] Admin     : Carlos Bourlemont (PIN: 2026, Pass: admin, Rol: ADMIN)")
        print(f"    [+] Bartender : Sofía Castillo    (PIN: 2468, Rol: BARTENDER)")
        print(f"    [+] Bartender : Alejandro Ruiz    (PIN: 7788, Rol: BARTENDER)")

        # ── 2. INSUMOS BASE ───────────────────────────────────────────────────
        print("\n[2/5] Insertando insumos base en mililitros (ml)...")
        insumo_champagne_brut = Producto(
            nombre="Champagne Brut (750 ml)",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=7500,       # 10 botellas de 750 ml
            stock_minimo_ml=750,
            unidad_medida="ml",
            imagen_url="/assets/img/champagne-brut.jpg"
        )
        insumo_gin_tanqueray = Producto(
            nombre="Gin Tanqueray (750 ml)",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("650.00"),
            stock_ml=7500,       # 10 botellas de 750 ml
            stock_minimo_ml=750,
            unidad_medida="ml",
            imagen_url="/assets/img/tanqueray.jpg"
        )
        insumo_cognac_hennessy = Producto(
            nombre="Cognac Hennessy (700 ml)",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("2600.00"),
            stock_ml=4900,       # 7 botellas de 700 ml
            stock_minimo_ml=700,
            unidad_medida="ml",
            imagen_url="/assets/img/hennessy.jpg"
        )
        insumo_jarabe = Producto(
            nombre="Jarabe/Sirope (1000 ml)",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=5000,       # 5 botellas de 1000 ml
            stock_minimo_ml=1000,
            unidad_medida="ml",
            imagen_url="/assets/img/sirope.jpg"
        )
        # Insumo base para Dom Pérignon
        insumo_dom_vintage = Producto(
            nombre="Dom Pérignon Vintage 2013",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("3800.00"),
            stock_ml=7500,       # 10 botellas de 750 ml
            stock_minimo_ml=1500,
            unidad_medida="ml",
            imagen_url="/assets/img/dom-perignon.jpg"
        )
        # Insumos complementarios para compatibilidad de suite
        insumo_tanqueray_ten = Producto(
            nombre="Gin Tanqueray No. TEN",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("650.00"),
            stock_ml=7500,
            stock_minimo_ml=1500,
            unidad_medida="ml"
        )
        insumo_moet = Producto(
            nombre="Moët & Chandon Impérial Brut",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("1200.00"),
            stock_ml=15000,
            stock_minimo_ml=3000,
            unidad_medida="ml"
        )
        insumo_limon = Producto(
            nombre="Jugo de Limón Fresco",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=3000,
            stock_minimo_ml=800,
            unidad_medida="ml"
        )

        db.add_all([
            insumo_champagne_brut,
            insumo_gin_tanqueray,
            insumo_cognac_hennessy,
            insumo_jarabe,
            insumo_dom_vintage,
            insumo_tanqueray_ten,
            insumo_moet,
            insumo_limon
        ])
        db.flush()
        print(f"    [+] Insumo : Champagne Brut (750 ml)   | Stock: {insumo_champagne_brut.stock_ml} ml")
        print(f"    [+] Insumo : Gin Tanqueray (750 ml)    | Stock: {insumo_gin_tanqueray.stock_ml} ml")
        print(f"    [+] Insumo : Cognac Hennessy (700 ml)  | Stock: {insumo_cognac_hennessy.stock_ml} ml")
        print(f"    [+] Insumo : Jarabe/Sirope (1000 ml)   | Stock: {insumo_jarabe.stock_ml} ml")
        print(f"    [+] Insumo : Dom Pérignon Vintage 2013 | Stock: {insumo_dom_vintage.stock_ml} ml")

        # ── 3. PRODUCTOS FINALES / CÓCTELES ────────────────────────────────────
        print("\n[3/5] Insertando cócteles y productos finales para venta...")
        coctel_copa_champagne = Producto(
            nombre="Copa Champagne Brut (150 ml)",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("260.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa",
            imagen_url="/assets/img/copa-champagne.jpg"
        )
        coctel_french_75 = Producto(
            nombre="French 75 Bourlemont",
            categoria=CategoriaProducto.COCTELES_AUTOR,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("185.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa",
            imagen_url="/assets/img/french-75.jpg"
        )
        coctel_dom_perignon = Producto(
            nombre="Dom Pérignon Vintage",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("3800.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="botella",
            imagen_url="/assets/img/dom-perignon.jpg"
        )

        db.add_all([coctel_copa_champagne, coctel_french_75, coctel_dom_perignon])
        db.flush()
        print(f"    [+] Cóctel : Copa Champagne Brut (150 ml) -> Q 260.00")
        print(f"    [+] Cóctel : French 75 Bourlemont         -> Q 185.00")
        print(f"    [+] Cóctel : Dom Pérignon Vintage         -> Q 3,800.00")

        # ── 4. RECETAS / ESCANDALLOS ──────────────────────────────────────────
        print("\n[4/5] Mapeando recetas y escandallos algorítmicos...")
        recetas = [
            # Copa Champagne Brut: descuenta 150 ml de Champagne Brut (750 ml)
            RecetaEscandallo(
                id_producto_final=coctel_copa_champagne.id_producto,
                id_insumo_base=insumo_champagne_brut.id_producto,
                cantidad_descontar_ml=150
            ),
            # French 75 Bourlemont:
            # - 90 ml Champagne Brut
            # - 45 ml Gin Tanqueray
            # - 15 ml Jarabe/Sirope
            RecetaEscandallo(
                id_producto_final=coctel_french_75.id_producto,
                id_insumo_base=insumo_champagne_brut.id_producto,
                cantidad_descontar_ml=90
            ),
            RecetaEscandallo(
                id_producto_final=coctel_french_75.id_producto,
                id_insumo_base=insumo_gin_tanqueray.id_producto,
                cantidad_descontar_ml=45
            ),
            RecetaEscandallo(
                id_producto_final=coctel_french_75.id_producto,
                id_insumo_base=insumo_jarabe.id_producto,
                cantidad_descontar_ml=15
            ),
            # Dom Pérignon Vintage: descuenta 750 ml de Dom Pérignon Vintage 2013
            RecetaEscandallo(
                id_producto_final=coctel_dom_perignon.id_producto,
                id_insumo_base=insumo_dom_vintage.id_producto,
                cantidad_descontar_ml=750
            )
        ]
        db.add_all(recetas)
        db.flush()
        print("    [+] Escandallo asignado: Copa Champagne Brut -> 150 ml Champagne Brut")
        print("    [+] Escandallo asignado: French 75 -> 90 ml Champagne + 45 ml Gin + 15 ml Jarabe")
        print("    [+] Escandallo asignado: Dom Pérignon Vintage -> 750 ml Dom Pérignon")

        # ── 5. TURNO DE CAJA & BITÁCORA ────────────────────────────────────────
        print("\n[5/5] Registrando arqueo de caja inicial y bitácora de auditoría...")
        arqueo_inicial = ArqueoCaja(
            id_usuario=bartender_mateo.id_usuario,
            fecha_apertura=now_gt - timedelta(hours=2),
            fondo_inicial=Decimal("1000.00"),
            estado=EstadoArqueo.ABIERTO
        )
        db.add(arqueo_inicial)

        bitacora = BitacoraAuditoria(
            id_usuario=admin_carlos.id_usuario,
            accion="INICIALIZACION_FASE_1",
            descripcion="Tablas regeneradas y datos semilla iniciales cargados en MySQL (XAMPP/InnoDB)."
        )
        db.add(bitacora)

        db.commit()
        print("\n" + "="*70)
        print("[OK] BASE DE DATOS 'bourlemontdb' REGENERADA Y POBLADA EXITOSAMENTE EN MYSQL")
        print("="*70)

    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] Fallo al sembrar la base de datos: {exc}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Regenera y puebla la base de datos MySQL para Bourlemont POS")
    parser.add_argument("--no-reset", action="store_true", help="No regenerar tablas, solo sembrar si está vacía")
    args = parser.parse_args()

    if not args.no_reset:
        regenerar_tablas()
    seed_database()


if __name__ == "__main__":
    main()
