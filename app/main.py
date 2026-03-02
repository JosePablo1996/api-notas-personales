from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import time
import os
from typing import Dict
from datetime import datetime

from app.database.connection import engine, close_db_connections, init_db, check_db_health, get_db_stats
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
    
    # Inicializar base de datos
    try:
        logger.info("🗄️  Inicializando base de datos...")
        init_db()
        
        # Verificar salud de la BD
        is_healthy, message = check_db_health()
        if is_healthy:
            logger.info("✅ Base de datos inicializada correctamente")
            
            # Mostrar estadísticas del pool
            stats = get_db_stats()
            logger.info(f"📊 Pool de conexiones: {stats}")
        else:
            logger.error(f"❌ Problema de salud en BD: {message}")
            
    except Exception as e:
        logger.error(f"❌ Error al inicializar base de datos: {str(e)}")
        raise
    
    logger.info("✅ Aplicación iniciada correctamente")
    logger.info("📚 Documentación disponible en /docs")
    logger.info(f"🌍 Servidor corriendo en: http://localhost:8000")
    
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
    * ⭐ Marcar notas como favoritas
    * 📦 Archivar notas
    * 🏷️ Sistema completo de etiquetas (tags)
    * 🎨 Colores personalizados para notas
    * 🔍 Búsqueda avanzada en título y contenido
    * 📊 Estadísticas detalladas
    * 🗑️ Papelera con soft delete
    * 🔄 Endpoints específicos para toggles
    * 📱 Optimizada para aplicaciones móviles
    
    ### Tecnologías:
    * FastAPI + Python 3.11
    * PostgreSQL + SQLAlchemy
    * Pydantic V2 para validaciones
    * Pooling optimizado de conexiones
    """,
    version="1.2.0",  # 👈 VERSIÓN ACTUALIZADA
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Soporte API",
        "email": "pabloquintanilla988@gmail.com",
        "url": "https://github.com/tu-usuario/notas-api"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Notes",
            "description": "📝 Operaciones CRUD para gestión de notas",
        },
        {
            "name": "Notes - Special Operations",
            "description": "✨ Operaciones especiales (toggle favorito, archivar, restaurar)",
        },
        {
            "name": "Trash",
            "description": "🗑️ Gestión de papelera (soft delete)",
        },
        {
            "name": "Stats",
            "description": "📊 Estadísticas y métricas",
        },
        {
            "name": "Health",
            "description": "💓 Endpoints de monitoreo y salud",
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
    expose_headers=[
        "X-Total-Count", 
        "X-Next-Page", 
        "X-Page-Size",
        "X-Process-Time",
        "X-DB-Pool-Stats"
    ],
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
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"
    
    # Logging de peticiones lentas
    if process_time > 1.0:  # Más de 1 segundo
        logger.warning(f"⚠️ Petición lenta: {request.method} {request.url.path} - {process_time:.2f}s")
    elif process_time > 0.5:  # Más de 0.5 segundos
        logger.info(f"⏱️ Petición moderada: {request.method} {request.url.path} - {process_time:.2f}s")
    
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logging de peticiones.
    """
    # No loguear peticiones a /health (demasiado ruido)
    if request.url.path != "/health":
        logger.info(f"📥 {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # No loguear respuestas de /health
        if request.url.path != "/health":
            logger.info(f"📤 {request.method} {request.url.path} - {response.status_code}")
        
        return response
    except Exception as e:
        logger.error(f"❌ Error en {request.method} {request.url.path}: {str(e)}")
        raise

@app.middleware("http")
async def add_db_pool_stats(request: Request, call_next):
    """
    Middleware para añadir estadísticas del pool de BD en desarrollo.
    """
    response = await call_next(request)
    
    # Solo añadir en desarrollo y para requests específicos
    if os.getenv("ENVIRONMENT") == "development" and request.url.path.startswith("/api/"):
        try:
            stats = get_db_stats()
            response.headers["X-DB-Pool-Stats"] = str(stats)
        except:
            pass
    
    return response


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
            "errors": errors,
            "timestamp": datetime.now().isoformat()
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
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
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
        "version": "1.2.0",
        "status": "operational",
        "features": {
            "notes": "✅ CRUD completo",
            "favorites": "✅ Notas favoritas",
            "archive": "✅ Notas archivadas",
            "tags": "✅ Sistema de etiquetas",
            "colors": "✅ Colores personalizados",
            "trash": "✅ Papelera (soft delete)",
            "search": "✅ Búsqueda avanzada",
            "stats": "✅ Estadísticas detalladas"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "📝 Notas": {
                "GET /api/v1/notes": "📋 Listar notas (con paginación y filtros)",
                "POST /api/v1/notes": "➕ Crear nota",
                "GET /api/v1/notes/{id}": "🔍 Obtener nota por ID",
                "PUT /api/v1/notes/{id}": "✏️ Actualizar nota",
                "DELETE /api/v1/notes/{id}": "🗑️ Mover a papelera"
            },
            "✨ Operaciones especiales": {
                "POST /api/v1/notes/{id}/toggle-favorite": "⭐ Alternar favorito",
                "POST /api/v1/notes/{id}/toggle-archived": "📦 Alternar archivado",
                "POST /api/v1/notes/{id}/restore": "🔄 Restaurar de papelera"
            },
            "🗑️ Papelera": {
                "GET /api/v1/notes/deleted/all": "📋 Ver notas eliminadas"
            },
            "📊 Estadísticas": {
                "GET /api/v1/notes/stats/summary": "📈 Estadísticas completas"
            }
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now().isoformat()
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
    - Pool de conexiones
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": None,  # Podrías calcularlo si guardas el start_time
        "checks": []
    }
    
    # Verificar conexión a base de datos
    is_healthy, message = check_db_health()
    health_status["checks"].append({
        "name": "database",
        "status": "healthy" if is_healthy else "unhealthy",
        "message": message
    })
    
    if not is_healthy:
        health_status["status"] = "unhealthy"
    
    # Añadir estadísticas del pool en desarrollo
    if os.getenv("ENVIRONMENT") == "development":
        try:
            pool_stats = get_db_stats()
            health_status["pool_stats"] = pool_stats
        except:
            pass
    
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
    import platform
    
    # Ocultar contraseña en DATABASE_URL
    db_url = os.getenv("DATABASE_URL", "not configured")
    if ":" in db_url and "@" in db_url:
        # Formato: postgresql://user:password@host/db
        parts = db_url.split("@")
        credentials = parts[0].split(":")
        if len(credentials) > 2:
            credentials[2] = "********"
            parts[0] = ":".join(credentials)
            db_url = "@".join(parts)
    
    return {
        "app_name": app.title,
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "dependencies": {
            "fastapi": "0.104.1+",
            "sqlalchemy": "2.0+",
            "pydantic": "2.0+"
        },
        "database": {
            "url": db_url,
            "pool_stats": get_db_stats() if os.getenv("ENVIRONMENT") == "development" else "hidden"
        },
        "cors": {
            "allowed_origins": os.getenv("ALLOWED_ORIGINS", "*").split(","),
            "exposed_headers": ["X-Total-Count", "X-Next-Page", "X-Page-Size", "X-Process-Time"]
        }
    }


@app.get(
    "/metrics",
    tags=["Health"],
    summary="Métricas de la API",
    description="Endpoint con métricas básicas de uso (solo en desarrollo)"
)
async def get_metrics():
    """
    Endpoint con métricas de uso (solo para desarrollo).
    """
    if os.getenv("ENVIRONMENT") != "development":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Endpoint solo disponible en desarrollo"}
        )
    
    # Aquí podrías implementar un contador de requests
    return {
        "message": "Métricas en desarrollo",
        "timestamp": datetime.now().isoformat(),
        "database_pool": get_db_stats()
    }


# ============================================
# Configuración adicional para producción
# ============================================

if os.getenv("ENVIRONMENT") == "production":
    logger.info("🔒 Modo producción: Configuración de seguridad aplicada")
    
    # Deshabilitar docs en producción (opcional - comentar si se quiere mantener)
    # app.docs_url = None
    # app.redoc_url = None
    # app.openapi_url = None
    
    # Middleware de seguridad recomendados
    # from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    # app.add_middleware(HTTPSRedirectMiddleware)
    
    # from fastapi.middleware.trustedhost import TrustedHostMiddleware
    # app.add_middleware(
    #     TrustedHostMiddleware,
    #     allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost").split(",")
    # )
    
    # from fastapi.middleware.gzip import GZipMiddleware
    # app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    logger.info("✅ Configuración de producción aplicada")
else:
    logger.info("🔧 Modo desarrollo: Configuración de debugging activada")