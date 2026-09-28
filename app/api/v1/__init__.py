from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.ordenes import router as ordenes_router
from app.api.v1.inventario import router as inventario_router
from app.api.v1.caja import router as caja_router
from app.api.v1.auditoria import router as auditoria_router
from app.api.v1.reportes import router as reportes_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(ordenes_router)
api_router.include_router(inventario_router)
api_router.include_router(caja_router)
api_router.include_router(auditoria_router)
api_router.include_router(reportes_router)
