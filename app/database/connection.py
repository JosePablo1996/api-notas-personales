from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv
import logging
from contextlib import contextmanager

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Obtener URL de la base de datos con validación
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Valor por defecto para desarrollo
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/notas_db"
    logger.warning("DATABASE_URL no encontrada en variables de entorno. Usando valor por defecto para desarrollo.")
    logger.warning("⚠️  CAMBIA LA CONTRASEÑA en production o en tu archivo .env")

# Configuración específica por tipo de base de datos
connect_args = {}
if "postgresql" in DATABASE_URL:
    connect_args = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
elif "sqlite" in DATABASE_URL:
    connect_args = {
        "check_same_thread": False
    }

# Configuración del Engine con Pooling optimizado
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Número de conexiones a mantener en el pool
    max_overflow=10,            # Conexiones extra bajo demanda
    pool_pre_ping=True,         # Verifica la conexión antes de usarla
    pool_recycle=3600,          # Recicla conexiones después de 1 hora
    echo=False,                 # Pon en True solo para ver las SQL en desarrollo
    pool_timeout=30,            # Tiempo máximo de espera para obtener una conexión
    connect_args=connect_args,
    # Para PostgreSQL, podemos añadir esto
    **({"execution_options": {"isolation_level": "AUTOCOMMIT"}} if "postgresql" in DATABASE_URL else {})
)

# Crear fábrica de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False      # Evita que los objetos expiren después de commit
)

def get_db():
    """
    Dependencia de FastAPI para obtener una sesión de base de datos.
    Se asegura de cerrar la sesión después de cada petición.
    """
    db = SessionLocal()
    try:
        logger.debug("Sesión de base de datos creada")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Error en la sesión de base de datos: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Sesión de base de datos cerrada")

@contextmanager
def get_db_context():
    """
    Context manager para usar la base de datos fuera de FastAPI.
    Útil para scripts, tareas programadas, etc.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error en contexto de BD: {str(e)}")
        raise
    finally:
        db.close()

def init_db():
    """
    Función de utilidad para inicializar la base de datos.
    Crea todas las tablas si no existen.
    """
    try:
        from app.database.base import Base
        from app.models.note import Note  # Asegúrate de importar tus modelos
        
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Base de datos inicializada correctamente")
        
        # Verificar conexión - CORREGIDO con text()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            logger.info(f"✅ Conexión a BD verificada: {result}")
            
    except SQLAlchemyError as e:
        logger.error(f"❌ Error al inicializar la base de datos: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {str(e)}")
        raise

def close_db_connections():
    """
    Cierra todas las conexiones del pool (útil para shutdown).
    """
    try:
        engine.dispose()
        logger.info("✅ Conexiones de base de datos cerradas")
    except Exception as e:
        logger.error(f"❌ Error al cerrar conexiones: {str(e)}")

def check_db_health():
    """
    Verifica la salud de la conexión a la base de datos.
    Útil para health checks.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Base de datos saludable"
    except Exception as e:
        logger.error(f"❌ Error en health check de BD: {str(e)}")
        return False, str(e)

def get_db_stats():
    """
    Obtiene estadísticas del pool de conexiones.
    Útil para monitoreo.
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "overflow": pool.overflow(),
        "total_connections": pool.total()
    }

# Para testing
def reset_db():
    """
    Reinicia la base de datos (solo para desarrollo/testing).
    """
    if "test" in DATABASE_URL or "localhost" in DATABASE_URL:
        from app.database.base import Base
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.warning("🔄 Base de datos reiniciada (solo para desarrollo)")
    else:
        logger.error("❌ No se puede reiniciar la BD en producción")
        raise Exception("No se permite reset_db en producción")