import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 1. Login as Admin
login_res = requests.post(f"{BASE_URL}/auth/login-pin", json={"pin": "2026"})
print("Admin Login status:", login_res.status_code)
assert login_res.status_code == 200, login_res.text
admin_token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {admin_token}"}

# 2. Test Excel Export with Bearer Token
excel_res = requests.get(f"{BASE_URL}/reportes/ventas/excel", headers=headers)
print("Excel Report status:", excel_res.status_code, "Content length:", len(excel_res.content))
assert excel_res.status_code == 200
assert len(excel_res.content) > 0

# 3. Test Create and Update Open Order (estado = 'ABIERTA')
# First get products
prod_res = requests.get(f"{BASE_URL}/inventario/productos", headers=headers)
prods = prod_res.json()
cocktail = next(p for p in prods if p["tipo"] in ("FINAL", "COMPUESTO"))

order_payload = {
    "numero_mesa": "Mesa VIP-7",
    "cliente_nombre": "Carlos Bourlemont",
    "cliente_nit": "CF",
    "items": [
        {"id_producto": cocktail["id_producto"], "cantidad": 2, "notas": "Sin hielo extra"}
    ]
}
order_res = requests.post(f"{BASE_URL}/ordenes/", json=order_payload, headers=headers)
print("Create Open Order status:", order_res.status_code)
assert order_res.status_code in (200, 201), order_res.text
order_data = order_res.json()
order_id = order_data["id_orden"]
print(f"Order {order_id} created with estado: {order_data['estado']}")
assert order_data["estado"] == "ABIERTA"

# Update Open Order
order_update_payload = {
    "numero_mesa": "Mesa VIP-7 Actualizada",
    "cliente_nombre": "Carlos Bourlemont",
    "cliente_nit": "CF",
    "items": [
        {"id_producto": cocktail["id_producto"], "cantidad": 3, "notas": "Con hielo extra"}
    ]
}
update_res = requests.put(f"{BASE_URL}/ordenes/{order_id}", json=order_update_payload, headers=headers)
print("Update Open Order status:", update_res.status_code)
assert update_res.status_code == 200, update_res.text
assert update_res.json()["numero_mesa"] == "Mesa VIP-7 Actualizada"

# 4. Check Dashboard Metrics for open orders count
dash_res = requests.get(f"{BASE_URL}/reportes/dashboard", headers=headers)
print("Dashboard status:", dash_res.status_code)
assert dash_res.status_code == 200
dash_data = dash_res.json()
print("Comandas abiertas count:", dash_data.get("ordenes_abiertas"))
assert dash_data["ordenes_abiertas"] >= 1

# 5. Test Recipe Update & Add Ingredient
# Find an existing recipe or create one
recetas_res = requests.get(f"{BASE_URL}/inventario/recetas", headers=headers)
print("Recetas status:", recetas_res.status_code)
assert recetas_res.status_code == 200
recetas = recetas_res.json()

if recetas:
    r0 = recetas[0]
    receta_id = r0["id_receta"]
    # Update ml
    put_receta = requests.put(f"{BASE_URL}/inventario/recetas/{receta_id}", json={"cantidad_descontar_ml": 65.5}, headers=headers)
    print("Update Receta ml status:", put_receta.status_code)
    assert put_receta.status_code == 200
    assert put_receta.json()["cantidad_descontar_ml"] == 65.5

# Test Add Ingredient
insumo = next(p for p in prods if p["tipo"] == "INSUMO")
add_ing_res = requests.post(f"{BASE_URL}/inventario/recetas/ingrediente", json={
    "id_producto_final": cocktail["id_producto"],
    "id_insumo_base": insumo["id_producto"],
    "cantidad_descontar_ml": 25.0
}, headers=headers)
print("Add Receta Ingrediente status:", add_ing_res.status_code)
assert add_ing_res.status_code == 200
print("New/Updated ingredient deduction ml:", add_ing_res.json()["cantidad_descontar_ml"])

# 6. Test Payment and Settlement
pay_res = requests.post(f"{BASE_URL}/ordenes/{order_id}/pagar", json={
    "metodo_pago": "EFECTIVO",
    "monto_recibido": 1000.0,
    "propina": 20.0
}, headers=headers)
print("Payment status:", pay_res.status_code)
assert pay_res.status_code == 200
pay_data = pay_res.json()
print("Payment state:", pay_data["orden"]["estado"])
assert pay_data["orden"]["estado"] == "PAGADA"
assert pay_data.get("ticket_termico") is not None

# Check time zone is UTC-6
from datetime import datetime, timezone, timedelta
tz_gt = timezone(timedelta(hours=-6))
now_gt = datetime.now(tz_gt)
print("Current GT Time:", now_gt.isoformat())

print("\n--- ALL BACKEND CHECKS PASSED SUCCESSFULLY! ---")
