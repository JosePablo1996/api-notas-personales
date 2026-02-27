from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Obtener URL de la base de datos con validación
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Valor por defecto para desarrollo
    DATABASE_URL = "postgresql://postgres:tu_contraseña@localhost:5432/notas_db"
    logger.warning("DATABASE_URL no encontrada en variables de entorno. Usando valor por defecto para desarrollo.")
    logger.warning("⚠️  CAMBIA LA CONTRASEÑA EN production o en tu archivo .env")

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
    connect_args={
        "connect_timeout": 10    # Timeout de conexión a la BD en segundos
    } if "postgresql" in DATABASE_URL else {}
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

def init_db():
    """
    Función de utilidad para inicializar la base de datos.
    Crea todas las tablas si no existen.
    """
    try:
        from app.database.base import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Base de datos inicializada correctamente")
    except SQLAlchemyError as e:
        logger.error(f"❌ Error al inicializar la base de datos: {str(e)}")
        raise

def close_db_connections():
    """
    Cierra todas las conexiones del pool (útil para shutdown).
    """
    engine.dispose()
    logger.info("Conexiones de base de datos cerradas")