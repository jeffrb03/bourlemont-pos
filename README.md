# BOURLEMONT POS & INVENTORY ENGINE
### Sistema Automatizado de Inventario por Escandallo (ml) y Facturación SAT FEL
**Champagne Bar Bourlemont — Ciudad Vieja, Sacatepéquez**

---

## 1. Visión General
**Bourlemont POS & Inventory Engine** es una solución Local-First de alta fidelidad desarrollada específicamente para el exclusivo Champagne Bar Bourlemont (barra 360° y servicio en mesas). Resuelve de raíz la facturación genérica y erradica las mermas invisibles de licores premium mediante el **descuento algorítmico y automático de mililitros (ml) por receta en cada orden cobrada**, garantizando trazabilidad total por usuario y resiliencia ante cortes de conectividad.

---

## 2. Stack Tecnológico
* **Backend:** Python 3.11+ con **FastAPI** (asíncrono, modular, documentación OpenAPI interactiva en `/docs`).
* **Base de Datos:** **MySQL 8.0+** con motor **InnoDB** obligatorio (bloqueos de fila, claves foráneas e integridad ACID).
  * *Modo de contingencia:* Detección automática y conmutación transparente a **SQLite local** si el servidor MySQL local no está levantado.
* **ORM:** **SQLAlchemy 2.0+** con mapeo declarativo moderno y transacciones atómicas explícitas (`with db.begin():`).
* **Validación de Datos:** **Pydantic V2** con tipado estricto.
* **Facturación Electrónica (FEL SAT Guatemala):** Patrón Adapter con:
  * `MockFacturacionService` (Driver local de alta fidelidad con UUIDs SAT válidos).
  * `InfileFelService` (Integración de dos pasos: firma con `signer-emisores.feel.com.gt` y certificación con `certificador.feel.com.gt` con soporte de contingencia `ERROR_OFFLINE`).
* **Generación de Reportes:** **openpyxl** para exportación de libros de auditoría y proyecciones en `.xlsx` con paleta Apple Tinted Dark y acentos dorados.
* **Frontend:** Single Page Application (SPA) modular en **HTML5 semántico, CSS3 moderno y Vanilla JavaScript (ES6+ Modules, Fetch API)**. Cero bundlers pesados, carga instantánea.
* **Diseño:** **Apple Tinted Dark Mode (HIG)**:
  * Canvas: `#0A0A0C`
  * Paneles: `#141416`
  * Teclas: `#1F1F23` (Hover: `#29292E`)
  * Acento Bourlemont Dorado: `#D4AF37` / `#F0C961`
  * Físicas hápticas: `transform: scale(0.96)` con curva Apple `cubic-bezier(0.2, 0.8, 0.2, 1)`.

---

## 3. Estructura del Proyecto
```
bourlemont-pos/
├── app/
│   ├── api/
│   │   ├── deps.py             # Inyección de dependencias (DB Session, Usuario actual)
│   │   └── v1/
│   │       ├── auth.py         # Login con PIN táctil y credenciales Admin
│   │       ├── ordenes.py      # Comandas y cobro atómico con escandallos
│   │       ├── inventario.py   # Gestión de botellas, ml y recetas
│   │       ├── caja.py         # Apertura y arqueo ciego de turno
│   │       ├── auditoria.py    # Modificación de pagos y bitácora inmutable
│   │       └── reportes.py     # Descargas en Excel (.xlsx) y métricas
│   ├── core/
│   │   ├── config.py           # Configuración Pydantic Settings (.env)
│   │   └── security.py         # Hasheo PBKDF2-HMAC y tokens de sesión
│   ├── db/
│   │   ├── base.py             # DeclarativeBase SQLAlchemy
│   │   └── session.py          # Engine con pre-ping y fallback MySQL/SQLite
│   ├── models/                 # Modelos ORM (Usuario, Producto, Receta, etc.)
│   ├── schemas/                # Schemas Pydantic V2
│   └── services/
│       ├── escandallo.py       # Algoritmo matemático de deducción de ml
│       ├── fel/                # Proveedores FEL SAT (Mock e Infile)
│       ├── excel_reports.py    # Generador openpyxl con estilos de lujo
│       └── printer.py          # Generador de comprobantes térmicos ESC/POS
├── frontend/
│   ├── index.html              # Login táctil con PIN Pad numérico
│   ├── pos.html                # Grilla de productos + Comanda lateral en vivo
│   ├── inventario.html         # Panel de existencias en ml y botellas
│   ├── recetas.html            # Asignador de escandallos por cóctel
│   ├── auditoria.html          # Corrección de pagos y visor de logs
│   ├── dashboard.html          # Panel gerencial y exportación de reportes
│   └── assets/
│       ├── css/
│       │   ├── apple-tinted.css # Variables del tema, botones elásticos y layout
│       │   └── pos.css          # Estilos de comanda, grilla y modales
│       └── js/
│           ├── api.js           # Cliente Fetch centralizado
│           ├── pos.js           # Lógica de venta y cobro en vivo
│           └── pinpad.js        # Manejo del teclado táctil de acceso
├── scripts/
│   ├── init_db.py              # Creación de tablas e inserción de datos semilla
│   └── start_kiosk.bat         # Lanzador silencioso en modo quiosco para Windows
├── tests/
│   └── test_bourlemont.py      # Suite completa de pruebas automatizadas
├── .env.example
├── .env
├── requirements.txt
└── main.py                     # Instancia principal de FastAPI y montaje estático
```

---

## 4. Credenciales de Acceso Semilla

| Rol | Nombre | PIN Rápido | Contraseña Admin |
| :--- | :--- | :---: | :--- |
| **BARTENDER** | Mateo Morales | `1234` | - |
| **BARTENDER** | Sofía Castillo | `2468` | - |
| **BARTENDER** | Alejandro Ruiz | `7788` | - |
| **ADMIN** | Carlos Bourlemont | `9999` | `admin_bourlemont_2026` |

---

## 5. Algoritmo Atómico de Escandallo
Al ejecutar el cobro de una comanda (`POST /api/v1/ordenes/{id_orden}/cobrar`), el sistema:
1. Abre una transacción SQL atómica.
2. Identifica los productos finales compuestos y consulta sus ingredientes en `recetas_escandallos`.
3. Aplica la fórmula:
   $$\text{descuento (ml)} = \text{cantidad vendida} \times \text{cantidad a descontar (ml)}$$
4. Actualiza con bloqueo de fila (`UPDATE productos SET stock_ml = stock_ml - :descuento WHERE id_producto = :insumo_id`).
5. Registra el pago en `transacciones_pago` y marca la orden como `PAGADA`.
6. Emite y certifica la factura electrónica FEL.
7. Genera el ticket térmico ESC/POS.
8. En caso de cualquier falla, ejecuta **ROLLBACK total automático**.

---

## 6. Ejecución y Puesta en Marcha

### A. Inicialización de la Base de Datos
```bash
python scripts/init_db.py
```

### B. Iniciar Servidor de Desarrollo
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### C. Despliegue en Modo Quiosco (Windows POS)
Hacer doble clic en:
```
scripts/start_kiosk.bat
```
El script iniciará el servidor en segundo plano y abrirá Google Chrome en modo aplicación de pantalla completa (`--app=http://localhost:8000`).

### D. Ejecución de Pruebas Unitarias
```bash
python -m pytest tests/test_bourlemont.py -v
```
Todas las pruebas de autenticación, deducción atómica de mililitros, auditoría administrativa y exportación en Excel se encuentran cubiertas al 100%.
