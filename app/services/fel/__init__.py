from app.core.config import settings
from app.services.fel.base import FacturacionProvider, FacturaResult
from app.services.fel.mock import MockFacturacionService
from app.services.fel.infile import InfileFelService

def get_fel_provider() -> FacturacionProvider:
    if settings.FEL_PROVIDER.upper() == "INFILE":
        return InfileFelService()
    return MockFacturacionService()

__all__ = ["FacturacionProvider", "FacturaResult", "MockFacturacionService", "InfileFelService", "get_fel_provider"]
