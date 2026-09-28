import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from main import app
from app.db.session import SessionLocal
from app.models.models import Producto, Orden, TransaccionPago, BitacoraAuditoria, EstadoOrden, MetodoPago

client = TestClient(app)

def test_login_bartender_pin():
    """Prueba el acceso rápido táctil con PIN de 4 dígitos."""
    response = client.post("/api/v1/auth/login-pin", json={"pin": "1234"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["usuario"]["nombre"] == "Mateo Morales"
    assert data["usuario"]["rol"] == "BARTENDER"

def test_login_admin_password():
    """Prueba el acceso de gerencia con contraseña."""
    response = client.post("/api/v1/auth/login-admin", json={
        "nombre": "Carlos Bourlemont",
        "password": "admin_bourlemont_2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["usuario"]["rol"] == "ADMIN"

def test_catalogo_productos():
    """Verifica la carga del catálogo con existencias en ml y cavas."""
    response = client.get("/api/v1/inventario/productos")
    assert response.status_code == 200
    productos = response.json()
    assert len(productos) > 0
    
    # Verificar existencia de cócteles de autor con escandallos
    french = next((p for p in productos if p["nombre"] == "French 75 Bourlemont"), None)
    assert french is not None
    assert len(french["recetas_como_final"]) > 0

def test_algoritmo_atomico_escandallo_y_cobro():
    """
    Prueba el algoritmo matemático de escandallo:
    Venta de 2x 'French 75 Bourlemont' debe descontar exactamente:
    - 2 * 45 ml = 90 ml de Tanqueray No. TEN
    - 2 * 90 ml = 180 ml de Moët & Chandon
    """
    db = SessionLocal()
    # Obtener stock inicial de insumos
    tanqueray_antes = db.query(Producto).filter(Producto.nombre == "Gin Tanqueray No. TEN").first().stock_ml
    moet_antes = db.query(Producto).filter(Producto.nombre == "Moët & Chandon Impérial Brut").first().stock_ml
    coctel_french = db.query(Producto).filter(Producto.nombre == "French 75 Bourlemont").first()
    db.close()

    # Login Bartender
    auth_res = client.post("/api/v1/auth/login-pin", json={"pin": "1234"}).json()
    token = auth_res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear Orden
    create_res = client.post("/api/v1/ordenes", headers=headers, json={
        "numero_mesa": "Barra 360 - Asiento 2",
        "items": [
            {"id_producto": coctel_french.id_producto, "cantidad": 2}
        ]
    })
    assert create_res.status_code == 200
    orden_creada = create_res.json()
    id_orden = orden_creada["id_orden"]
    assert float(orden_creada["total"]) == 370.00

    # 2. Cobrar Orden
    cobro_res = client.post(f"/api/v1/ordenes/{id_orden}/cobrar", headers=headers, json={
        "metodo_pago": "EFECTIVO",
        "monto_pagado": 370.00,
        "propina": 37.00,
        "nit_receptor": "CF",
        "nombre_receptor": "CONSUMIDOR FINAL"
    })
    assert cobro_res.status_code == 200
    data_cobro = cobro_res.json()
    assert data_cobro["success"] is True
    assert data_cobro["orden"]["estado"] == "PAGADA"
    assert data_cobro["factura"]["estado_certificacion"] == "CERTIFICADA"
    assert "BOURLEMONT CHAMPAGNE BAR" in data_cobro["ticket_termico"]

    # 3. Validar deducción exacta en mililitros
    db2 = SessionLocal()
    tanqueray_despues = db2.query(Producto).filter(Producto.nombre == "Gin Tanqueray No. TEN").first().stock_ml
    moet_despues = db2.query(Producto).filter(Producto.nombre == "Moët & Chandon Impérial Brut").first().stock_ml
    db2.close()

    assert tanqueray_despues == tanqueray_antes - 90
    assert moet_despues == moet_antes - 180

def test_auditoria_cambio_metodo_pago():
    """Prueba la corrección de un método de pago por el Administrador con bitácora."""
    # Login Admin
    admin_auth = client.post("/api/v1/auth/login-admin", json={
        "nombre": "Carlos Bourlemont",
        "password": "admin_bourlemont_2026"
    }).json()
    token = admin_auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Obtener un pago existente
    pagos = client.get("/api/v1/auditoria/pagos", headers=headers).json()
    assert len(pagos) > 0
    pago_a_modificar = pagos[0]

    # Cambiar de método con justificación obligatoria
    nuevo_metodo = "TARJETA_MASTERCARD" if pago_a_modificar["metodo_pago"] != "TARJETA_MASTERCARD" else "TRANSFERENCIA"
    corr_res = client.post("/api/v1/auditoria/cambiar-metodo-pago", headers=headers, json={
        "id_pago": pago_a_modificar["id_pago"],
        "nuevo_metodo_pago": nuevo_metodo,
        "motivo": "Corrección de prueba: error al seleccionar voucher en barra 360"
    })
    assert corr_res.status_code == 200
    assert corr_res.json()["success"] is True

    # Verificar que el log inmutable exista
    logs = client.get("/api/v1/auditoria/logs", headers=headers).json()
    ultimo_log = logs[0]
    assert ultimo_log["accion"] == "CAMBIO_METODO_PAGO"
    assert "error al seleccionar voucher" in ultimo_log["descripcion"]

def test_reporte_excel_ventas():
    """Verifica la generación y streaming en memoria del libro Excel con las 3 hojas."""
    admin_auth = client.post("/api/v1/auth/login-admin", json={
        "nombre": "Carlos Bourlemont",
        "password": "admin_bourlemont_2026"
    }).json()
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    response = client.get("/api/v1/reportes/ventas/excel", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(response.content) > 1000
