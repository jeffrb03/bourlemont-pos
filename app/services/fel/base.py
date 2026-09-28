from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from app.models.models import Orden, EstadoFEL

@dataclass
class FacturaResult:
    uuid_autorizacion: Optional[str]
    serie: Optional[str]
    numero_dte: Optional[str]
    fecha_certificacion: Optional[str]
    nit_receptor: str
    nombre_receptor: str
    estado: EstadoFEL
    xml_firmado: Optional[str] = None
    mensaje_error: Optional[str] = None

class FacturacionProvider(ABC):
    """Interfaz abstracta para proveedores de Facturación Electrónica SAT (FEL)."""

    @abstractmethod
    def certificar_factura(self, orden: Orden, nit_receptor: str, nombre_receptor: str) -> FacturaResult:
        """Certifica una factura DTE ante la SAT / Certificador FEL."""
        pass

    @abstractmethod
    def anular_factura(self, uuid_autorizacion: str, motivo: str) -> bool:
        """Anula una factura certificada."""
        pass
