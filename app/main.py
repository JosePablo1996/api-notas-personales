from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import engine
from app.database.base import Base
from app.models import note
from app.routes.notes import router as notes_router

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Notas Personales",
    description="API para gestión de notas - Proyecto para app Android",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(notes_router)

@app.get("/")
def root():
    return {
        "message": "API de Notas Personales",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "GET /api/v1/notes": "Listar notas",
            "POST /api/v1/notes": "Crear nota",
            "GET /api/v1/notes/{id}": "Obtener nota",
            "PUT /api/v1/notes/{id}": "Actualizar nota",
            "DELETE /api/v1/notes/{id}": "Eliminar nota"
        }
    }