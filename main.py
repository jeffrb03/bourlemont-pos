import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.api.v1 import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas si no existen (en MySQL o SQLite fallback)
    Base.metadata.create_all(bind=engine)
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            cols = conn.execute(text("SHOW COLUMNS FROM usuarios LIKE 'foto_url'")).fetchall()
            if not cols:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN foto_url VARCHAR(255) NULL"))
    except Exception:
        pass
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Sistema automatizado de inventario y facturación para el Champagne Bar Bourlemont en Ciudad Vieja, Sacatepéquez.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Habilitar CORS para cliente local y red local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar routers API v1
app.include_router(api_router)

# Alias para rutas compatibles con especificación (/api/ordenes/..., /api/reportes/..., /api/usuarios/...)
from app.api.v1.ordenes import router as alias_ordenes
from app.api.v1.reportes import router as alias_reportes
from app.api.v1.usuarios import router as alias_usuarios
app.include_router(alias_ordenes, prefix="/api")
app.include_router(alias_reportes, prefix="/api")
app.include_router(alias_usuarios, prefix="/api")

# Montar estáticos del frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    assets_dir = os.path.join(frontend_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
def index():
    """Redirige al login táctil de entrada."""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Bourlemont POS Backend Operativo", "docs": "/docs"}

@app.get("/{page}.html")
def serve_html_pages(page: str):
    """Permite navegar directamente a /pos.html, /inventario.html, etc."""
    page_file = os.path.join(frontend_dir, f"{page}.html")
    if os.path.exists(page_file):
        return FileResponse(page_file)
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
