import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from app.core.config import settings

logger = logging.getLogger("bourlemont.db")

def create_configured_engine():
    db_url = settings.DATABASE_URL
    is_sqlite = db_url.startswith("sqlite")
    
    # Intento de conexión con MySQL si está configurado
    if not is_sqlite and settings.FALLBACK_TO_SQLITE:
        try:
            test_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={"connect_timeout": 2}
            )
            # Prueba de handshake rápido
            with test_engine.connect() as conn:
                pass
            logger.info(f"Conectado exitosamente a la base de datos MySQL: {db_url}")
            return test_engine
        except Exception as e:
            logger.warning(
                f"No se pudo conectar a MySQL ({e}). "
                f"Activando modo de contingencia local SQLite ({settings.SQLITE_URL})."
            )
            db_url = settings.SQLITE_URL
            is_sqlite = True

    if is_sqlite:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )
        # Habilitar claves foráneas en SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        return engine
    else:
        return create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600
        )

engine = create_configured_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
