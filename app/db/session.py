import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger("bourlemont.db")

def create_configured_engine():
    """
    Crea el engine de SQLAlchemy para MySQL (XAMPP/InnoDB).
    Conexión estricta obligatoria: Sin fallback automático a SQLite.
    """
    db_url = settings.DATABASE_URL
    if not db_url.startswith("mysql"):
        raise RuntimeError(
            f"Configuración inválida: Se requiere conexión estricta a MySQL. Recibido: {db_url}"
        )

    # --- MySQL principal estricto ---
    try:
        mysql_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": 5, "charset": "utf8mb4"},
        )
        # Handshake real para detectar fallo temprano
        with mysql_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"✓ Conectado a MySQL: {db_url.split('@')[-1]}")
        return mysql_engine

    except Exception as exc:
        logger.critical(
            "Error crítico: No se pudo conectar a MySQL (XAMPP). "
            "El fallback automático a SQLite está deshabilitado."
        )
        raise RuntimeError(
            f"Fallo de conexión estricta a MySQL: {exc}\n"
            "Solución: Inicia XAMPP (Apache + MySQL) y asegúrate de que exista la base 'bourlemontdb'."
        ) from exc


engine = create_configured_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
