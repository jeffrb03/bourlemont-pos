import sys
import os
from decimal import Decimal
from datetime import datetime, timedelta

# Asegurar path raíz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def seed_database():
    print("Iniciando creación de tablas y sembrado de datos en Bourlemont POS...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Verificar si ya existen usuarios
        if db.query(Usuario).count() > 0:
            print("La base de datos ya contiene registros. Omitiendo seed inicial.")
            return

        # 1. USUARIOS (1 Administrador y 3 Bartenders)
        print("Registrando equipo de bar...")
        admin = Usuario(
            nombre="Carlos Bourlemont",
            pin_hash=hash_pin("9999"),
            password_hash=hash_password("admin_bourlemont_2026"),
            rol=RolUsuario.ADMIN,
            activo=True
        )
        b1 = Usuario(
            nombre="Mateo Morales",
            pin_hash=hash_pin("1234"),
            rol=RolUsuario.BARTENDER,
            activo=True
        )
        b2 = Usuario(
            nombre="Sofía Castillo",
            pin_hash=hash_pin("2468"),
            rol=RolUsuario.BARTENDER,
            activo=True
        )
        b3 = Usuario(
            nombre="Alejandro Ruiz",
            pin_hash=hash_pin("7788"),
            rol=RolUsuario.BARTENDER,
            activo=True
        )
        db.add_all([admin, b1, b2, b3])
        db.flush()

        # 2. INSUMOS BASE Y LICORES (Medidos en ml para escandallo)
        print("Registrando cavas, licores premium e insumos base...")
        # Champagnes
        p_dom = Producto(
            nombre="Dom Pérignon Vintage 2013",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.FINAL,
            precio_venta=Decimal("3800.00"),
            stock_ml=7500,  # 10 botellas
            stock_minimo_ml=2250,
            unidad_medida="ml"
        )
        p_veuve = Producto(
            nombre="Veuve Clicquot Yellow Label Brut",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.FINAL,
            precio_venta=Decimal("1450.00"),
            stock_ml=15000, # 20 botellas
            stock_minimo_ml=3000,
            unidad_medida="ml"
        )
        p_moet = Producto(
            nombre="Moët & Chandon Impérial Brut",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.FINAL,
            precio_venta=Decimal("1200.00"),
            stock_ml=15000, # 20 botellas
            stock_minimo_ml=3000,
            unidad_medida="ml"
        )
        p_krug = Producto(
            nombre="Krug Grande Cuvée 170th Edition",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.FINAL,
            precio_venta=Decimal("5200.00"),
            stock_ml=4500,  # 6 botellas
            stock_minimo_ml=1500,
            unidad_medida="ml"
        )

        # Licores Premium
        p_hennessy = Producto(
            nombre="Cognac Hennessy XO",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("2600.00"),
            stock_ml=3750,  # 5 botellas
            stock_minimo_ml=750,
            unidad_medida="ml"
        )
        p_tanqueray = Producto(
            nombre="Gin Tanqueray No. TEN",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("650.00"),
            stock_ml=7500,  # 10 botellas
            stock_minimo_ml=1500,
            unidad_medida="ml"
        )
        p_macallan = Producto(
            nombre="The Macallan 12 Double Cask",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("1350.00"),
            stock_ml=6000,  # 8 botellas
            stock_minimo_ml=1500,
            unidad_medida="ml"
        )
        p_campari = Producto(
            nombre="Campari Milano Bitter",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("380.00"),
            stock_ml=4500,
            stock_minimo_ml=750,
            unidad_medida="ml"
        )
        p_vermouth = Producto(
            nombre="Vermouth Carpano Antica Formula",
            categoria=CategoriaProducto.LICORES,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("450.00"),
            stock_ml=5000,
            stock_minimo_ml=1000,
            unidad_medida="ml"
        )

        # Insumos Bar
        p_jarabe = Producto(
            nombre="Jarabe Simple Artesanal Bourlemont",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=5000,
            stock_minimo_ml=1000,
            unidad_medida="ml"
        )
        p_limon = Producto(
            nombre="Jugo de Limón Amarillo Eureka Fresco",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=3000,
            stock_minimo_ml=800,
            unidad_medida="ml"
        )
        p_angostura = Producto(
            nombre="Angostura Aromatic Bitters",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=600,
            stock_minimo_ml=150,
            unidad_medida="ml"
        )
        p_durazno = Producto(
            nombre="Puré de Durazno Blanco Natural",
            categoria=CategoriaProducto.INSUMOS_BASE,
            tipo=TipoProducto.INSUMO,
            precio_venta=Decimal("0.00"),
            stock_ml=4000,
            stock_minimo_ml=1000,
            unidad_medida="ml"
        )

        db.add_all([
            p_dom, p_veuve, p_moet, p_krug,
            p_hennessy, p_tanqueray, p_macallan, p_campari, p_vermouth,
            p_jarabe, p_limon, p_angostura, p_durazno
        ])
        db.flush()

        # 3. CÓCTELES DE AUTOR Y COPAS (Productos Finales Compuestos)
        print("Registrando cócteles de autor y copas por porción...")
        c_french = Producto(
            nombre="French 75 Bourlemont",
            categoria=CategoriaProducto.COCTELES_AUTOR,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("185.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa"
        )
        c_mimosa = Producto(
            nombre="Royal Mimosa Bourlemont",
            categoria=CategoriaProducto.COCTELES_AUTOR,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("175.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa"
        )
        c_imperial = Producto(
            nombre="Champagne Cocktail Impérial",
            categoria=CategoriaProducto.COCTELES_AUTOR,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("210.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa"
        )
        c_negroni = Producto(
            nombre="Negroni Sbagliato Bourlemont",
            categoria=CategoriaProducto.COCTELES_AUTOR,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("195.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa"
        )
        c_copa_veuve = Producto(
            nombre="Copa Veuve Clicquot Brut (150 ml)",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("260.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa"
        )
        c_copa_dom = Producto(
            nombre="Copa Dom Pérignon Vintage (150 ml)",
            categoria=CategoriaProducto.CHAMPAGNE,
            tipo=TipoProducto.COMPUESTO,
            precio_venta=Decimal("680.00"),
            stock_ml=0,
            stock_minimo_ml=0,
            unidad_medida="copa"
        )

        db.add_all([c_french, c_mimosa, c_imperial, c_negroni, c_copa_veuve, c_copa_dom])
        db.flush()

        # 4. RECETAS / ESCANDALLOS EN MILILITROS
        print("Mapeando escandallos matemáticos por receta en ml...")
        recetas = [
            # French 75: 45ml Gin + 25ml Limón + 15ml Jarabe + 90ml Champagne Moët
            RecetaEscandallo(id_producto_final=c_french.id_producto, id_insumo_base=p_tanqueray.id_producto, cantidad_descontar_ml=45),
            RecetaEscandallo(id_producto_final=c_french.id_producto, id_insumo_base=p_limon.id_producto, cantidad_descontar_ml=25),
            RecetaEscandallo(id_producto_final=c_french.id_producto, id_insumo_base=p_jarabe.id_producto, cantidad_descontar_ml=15),
            RecetaEscandallo(id_producto_final=c_french.id_producto, id_insumo_base=p_moet.id_producto, cantidad_descontar_ml=90),

            # Royal Mimosa: 60ml Puré Durazno + 120ml Veuve Clicquot
            RecetaEscandallo(id_producto_final=c_mimosa.id_producto, id_insumo_base=p_durazno.id_producto, cantidad_descontar_ml=60),
            RecetaEscandallo(id_producto_final=c_mimosa.id_producto, id_insumo_base=p_veuve.id_producto, cantidad_descontar_ml=120),

            # Champagne Cocktail Imperial: 30ml Hennessy XO + 5ml Angostura + 10ml Jarabe + 120ml Veuve Clicquot
            RecetaEscandallo(id_producto_final=c_imperial.id_producto, id_insumo_base=p_hennessy.id_producto, cantidad_descontar_ml=30),
            RecetaEscandallo(id_producto_final=c_imperial.id_producto, id_insumo_base=p_angostura.id_producto, cantidad_descontar_ml=5),
            RecetaEscandallo(id_producto_final=c_imperial.id_producto, id_insumo_base=p_jarabe.id_producto, cantidad_descontar_ml=10),
            RecetaEscandallo(id_producto_final=c_imperial.id_producto, id_insumo_base=p_veuve.id_producto, cantidad_descontar_ml=120),

            # Negroni Sbagliato: 30ml Campari + 30ml Vermouth Carpano + 60ml Moët
            RecetaEscandallo(id_producto_final=c_negroni.id_producto, id_insumo_base=p_campari.id_producto, cantidad_descontar_ml=30),
            RecetaEscandallo(id_producto_final=c_negroni.id_producto, id_insumo_base=p_vermouth.id_producto, cantidad_descontar_ml=30),
            RecetaEscandallo(id_producto_final=c_negroni.id_producto, id_insumo_base=p_moet.id_producto, cantidad_descontar_ml=60),

            # Copa Veuve: 150ml Veuve Clicquot
            RecetaEscandallo(id_producto_final=c_copa_veuve.id_producto, id_insumo_base=p_veuve.id_producto, cantidad_descontar_ml=150),

            # Copa Dom Pérignon: 150ml Dom Pérignon
            RecetaEscandallo(id_producto_final=c_copa_dom.id_producto, id_insumo_base=p_dom.id_producto, cantidad_descontar_ml=150)
        ]
        db.add_all(recetas)
        db.flush()

        # 5. TURNO DE CAJA ABIERTO INICIAL (Listo para operar)
        print("Abriendo turno de caja activo con fondo inicial de Q 1,000.00...")
        arqueo_inicial = ArqueoCaja(
            id_usuario=b1.id_usuario,
            fecha_apertura=datetime.utcnow() - timedelta(hours=3),
            fondo_inicial=Decimal("1000.00"),
            estado=EstadoArqueo.ABIERTO
        )
        db.add(arqueo_inicial)
        
        # 6. ÓRDENES DE MUESTRA COBRADAS (Para visualizar reportes y auditoría)
        print("Registrando órdenes iniciales de prueba...")
        ord1 = Orden(
            numero_mesa="Barra 360 - Asiento 1",
            id_usuario_creacion=b1.id_usuario,
            estado=EstadoOrden.PAGADA,
            fecha_creacion=datetime.utcnow() - timedelta(hours=2),
            fecha_cierre=datetime.utcnow() - timedelta(hours=1, minutes=45),
            total=Decimal("370.00")
        )
        db.add(ord1)
        db.flush()

        d1 = DetalleOrden(id_orden=ord1.id_orden, id_producto=c_french.id_producto, cantidad=2, precio_unitario=Decimal("185.00"), subtotal=Decimal("370.00"))
        pago1 = TransaccionPago(
            id_orden=ord1.id_orden,
            id_usuario_cobro=b1.id_usuario,
            metodo_pago=MetodoPago.TARJETA_VISA,
            monto_pagado=Decimal("370.00"),
            propina=Decimal("37.00"),
            fecha_transaccion=datetime.utcnow() - timedelta(hours=1, minutes=45)
        )
        fel1 = FacturaFEL(
            id_orden=ord1.id_orden,
            uuid_autorizacion="48F6C2A1-94E5-4C67-B91F-3D248D93FA10",
            serie="BLM26",
            numero_dte=f"{ord1.id_orden:09d}",
            fecha_certificacion=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S-06:00"),
            nit_receptor="CF",
            nombre_receptor="CONSUMIDOR FINAL",
            estado_certificacion=EstadoFEL.CERTIFICADA
        )
        db.add_all([d1, pago1, fel1])

        # Orden abierta actual en mesa 4
        ord_activa = Orden(
            numero_mesa="Mesa 4 (Terraza)",
            id_usuario_creacion=b2.id_usuario,
            estado=EstadoOrden.ABIERTA,
            fecha_creacion=datetime.utcnow() - timedelta(minutes=25),
            total=Decimal("470.00")
        )
        db.add(ord_activa)
        db.flush()

        d2_1 = DetalleOrden(id_orden=ord_activa.id_orden, id_producto=c_copa_veuve.id_producto, cantidad=1, precio_unitario=Decimal("260.00"), subtotal=Decimal("260.00"))
        d2_2 = DetalleOrden(id_orden=ord_activa.id_orden, id_producto=c_imperial.id_producto, cantidad=1, precio_unitario=Decimal("210.00"), subtotal=Decimal("210.00"))
        db.add_all([d2_1, d2_2])

        # Bitácora inicial
        log1 = BitacoraAuditoria(
            id_usuario=admin.id_usuario,
            accion="INICIALIZACION_SISTEMA",
            descripcion="Inicialización del sistema Bourlemont POS y sembrado de recetas de coctelería y cavas."
        )
        db.add(log1)

        db.commit()
        print("\n¡Sembrado completado exitosamente en Bourlemont POS!")
        print("-------------------------------------------------------------")
        print("USUARIOS PREPARADOS:")
        print("  • Bartender: Mateo Morales   (PIN: 1234)")
        print("  • Bartender: Sofía Castillo  (PIN: 2468)")
        print("  • Bartender: Alejandro Ruiz  (PIN: 7788)")
        print("  • Admin:     Carlos Bourlemont (PIN: 9999 / Pass: admin_bourlemont_2026)")
        print("-------------------------------------------------------------")

    except Exception as e:
        db.rollback()
        print(f"Error al inicializar base de datos: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
