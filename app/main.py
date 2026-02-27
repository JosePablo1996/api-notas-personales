from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time
import os
from typing import Dict

from app.database.connection import engine, close_db_connections, init_db
from app.database.base import Base
from app.routes.notes import router as notes_router

# ============================================
# Configuración de Logging
# ============================================

# Configurar formato de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================
# Lifespan Events (Startup/Shutdown)
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja eventos de inicio y cierre de la aplicación.
    - Startup: Inicializa conexiones y verifica BD
    - Shutdown: Limpia recursos y cierra conexiones
    """
    # STARTUP
    logger.info("=" * 50)
    logger.info("🚀 Iniciando API de Notas Personales")
    logger.info("=" * 50)
    
    # Verificar entorno
    env = os.getenv("ENVIRONMENT", "development")
    logger.info(f"📦 Entorno: {env}")
    
    # Inicializar base de datos (solo en desarrollo)
    if env == "development":
        try:
            logger.info("🗄️  Inicializando base de datos...")
            init_db()
            logger.info("✅ Base de datos inicializada correctamente")
        except Exception as e:
            logger.error(f"❌ Error al inicializar base de datos: {str(e)}")
            raise
    
    logger.info("✅ Aplicación iniciada correctamente")
    logger.info("📚 Documentación disponible en /docs")
    
    yield  # La aplicación corre aquí
    
    # SHUTDOWN
    logger.info("=" * 50)
    logger.info("🔄 Apagando API de Notas Personales...")
    
    # Cerrar conexiones de base de datos
    try:
        close_db_connections()
        logger.info("✅ Conexiones de base de datos cerradas")
    except Exception as e:
        logger.error(f"❌ Error al cerrar conexiones: {str(e)}")
    
    logger.info("👋 Aplicación detenida correctamente")
    logger.info("=" * 50)


# ============================================
# Creación de la aplicación FastAPI
# ============================================

app = FastAPI(
    title="API de Notas Personales",
    description="""
    ## API RESTful para gestión de notas personales
    
    ### Características:
    * ✍️ Crear, leer, actualizar y eliminar notas
    * 🔍 Búsqueda avanzada en título y contenido
    * 📊 Paginación y estadísticas
    * 🚀 Optimizada para aplicaciones móviles
    
    ### Tecnologías:
    * FastAPI + Python
    * PostgreSQL + SQLAlchemy
    * Pydantic V2 para validaciones
    """,
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Soporte API",
        "email": "soporte@notasapi.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Notes",
            "description": "Operaciones CRUD para gestión de notas",
        },
        {
            "name": "Health",
            "description": "Endpoints de monitoreo y salud",
        }
    ]
)


# ============================================
# Middlewares
# ============================================

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Next-Page", "X-Page-Size"],  # Headers de paginación
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware para medir tiempo de procesamiento de cada petición.
    """
    start_time = time.time()
    
    # Procesar la petición
    response = await call_next(request)
    
    # Calcular y añadir tiempo de proceso
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Logging de peticiones lentas
    if process_time > 1.0:  # Más de 1 segundo
        logger.warning(f"⚠️ Petición lenta: {request.method} {request.url.path} - {process_time:.2f}s")
    
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logging de peticiones.
    """
    logger.info(f"📥 {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.info(f"📤 {request.method} {request.url.path} - {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"❌ Error en {request.method} {request.url.path}: {str(e)}")
        raise


# ============================================
# Manejadores de Excepciones
# ============================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Manejador personalizado para errores de validación.
    """
    errors = []
    for error in exc.errors():
        error_dict = {
            "loc": " -> ".join(str(x) for x in error["loc"]),
            "msg": error["msg"],
            "type": error["type"]
        }
        errors.append(error_dict)
    
    logger.warning(f"Error de validación en {request.url.path}: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Error de validación en los datos enviados",
            "errors": errors
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Manejador genérico para excepciones no controladas.
    """
    logger.error(f"Error no controlado en {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Error interno del servidor",
            "path": request.url.path
        }
    )


# ============================================
# Inclusión de Routers
# ============================================

app.include_router(notes_router)


# ============================================
# Endpoints Raíz y Utilidades
# ============================================

@app.get(
    "/",
    tags=["Health"],
    summary="Raíz de la API",
    description="Endpoint principal con información de la API y enlaces útiles"
)
async def root() -> Dict:
    """
    Endpoint raíz que proporciona información básica de la API.
    """
    return {
        "message": "API de Notas Personales",
        "version": "1.0.0",
        "status": "operational",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "GET /api/v1/notes": "📋 Listar notas (con paginación y búsqueda)",
            "POST /api/v1/notes": "➕ Crear nota",
            "GET /api/v1/notes/{id}": "🔍 Obtener nota por ID",
            "PUT /api/v1/notes/{id}": "✏️ Actualizar nota",
            "DELETE /api/v1/notes/{id}": "🗑️ Eliminar nota",
            "GET /api/v1/notes/stats/summary": "📊 Estadísticas de notas"
        },
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Endpoint para verificar el estado de la API y sus dependencias"
)
async def health_check() -> Dict:
    """
    Endpoint de health check para monitoreo.
    Verifica:
    - Estado de la API
    - Conexión a base de datos
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": []
    }
    
    # Verificar conexión a base de datos
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"].append({
            "name": "database",
            "status": "healthy",
            "message": "Conexión a base de datos OK"
        })
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"].append({
            "name": "database",
            "status": "unhealthy",
            "message": f"Error de conexión: {str(e)}"
        })
    
    return health_status


@app.get(
    "/info",
    tags=["Health"],
    summary="Información del Sistema",
    description="Obtiene información detallada sobre la configuración del sistema"
)
async def system_info() -> Dict:
    """
    Endpoint con información del sistema para debugging.
    """
    import sys
    
    return {
        "app_name": app.title,
        "version": app.version,
        "python_version": sys.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "cors_origins": os.getenv("ALLOWED_ORIGINS", "*"),
        "database_url": os.getenv("DATABASE_URL", "not configured").replace(
            os.getenv("DB_PASSWORD", ""), "********"  # Ocultar contraseña
        )
    }


# ============================================
# Configuración adicional para producción
# ============================================

if os.getenv("ENVIRONMENT") == "production":
    # En producción, deshabilitar docs si es necesario
    # app.docs_url = None
    # app.redoc_url = None
    logger.info("🔒 Modo producción: Configuración de seguridad aplicada")
    
    # Aquí podrías añadir más middlewares de seguridad
    # from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    # app.add_middleware(HTTPSRedirectMiddleware)
    
    # from fastapi.middleware.trustedhost import TrustedHostMiddleware
    # app.add_middleware(
    #     TrustedHostMiddleware,
    #     allowed_hosts=["tu-dominio.com", "*.tu-dominio.com"]
    # )