from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from datetime import datetime
from typing import Optional, List
import re

# ============================================
# Modelos Base
# ============================================

class NoteBase(BaseModel):
    """
    Modelo base para notas con campos comunes.
    """
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Título de la nota (mínimo 3 caracteres, máximo 200)",
        examples=["Mi primera nota", "Lista de compras"]
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Contenido de la nota (no puede estar vacío)",
        examples=["Este es el contenido de mi nota...", "Leche, pan, huevos"]
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """
        Valida y sanitiza el título.
        - Elimina espacios extras
        - Capitaliza primera letra
        """
        if not v or not v.strip():
            raise ValueError('El título no puede estar vacío')
        
        # Limpiar espacios extras
        cleaned = ' '.join(v.strip().split())
        
        # Capitalizar primera letra
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """
        Valida y sanitiza el contenido.
        - Elimina espacios al inicio y final
        - Mantiene saltos de línea
        """
        if not v or not v.strip():
            raise ValueError('El contenido no puede estar vacío')
        
        # Eliminar espacios al inicio y final pero mantener formato
        return v.strip()
    
    @model_validator(mode='after')
    def check_title_content(self) -> 'NoteBase':
        """
        Validación a nivel de modelo.
        Verifica que título y contenido no sean iguales.
        """
        if self.title and self.content and self.title.strip().lower() == self.content.strip().lower():
            raise ValueError('El título y el contenido no pueden ser idénticos')
        return self


# ============================================
# Modelos para Creación
# ============================================

class NoteCreate(NoteBase):
    """
    Modelo para crear una nueva nota.
    Hereda todas las validaciones de NoteBase.
    """
    pass


# ============================================
# Modelos para Actualización
# ============================================

class NoteUpdate(BaseModel):
    """
    Modelo para actualizar una nota existente.
    Todos los campos son opcionales.
    """
    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=200,
        description="Nuevo título (opcional)",
        examples=["Título actualizado"]
    )
    content: Optional[str] = Field(
        None,
        min_length=1,
        description="Nuevo contenido (opcional)",
        examples=["Contenido actualizado..."]
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Valida título si se proporciona"""
        if v is not None:
            if not v.strip():
                raise ValueError('El título no puede estar vacío')
            # Limpiar espacios extras
            cleaned = ' '.join(v.strip().split())
            # Capitalizar primera letra
            return cleaned[0].upper() + cleaned[1:]
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Valida contenido si se proporciona"""
        if v is not None:
            if not v.strip():
                raise ValueError('El contenido no puede estar vacío')
            return v.strip()
        return v
    
    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'NoteUpdate':
        """
        Verifica que al menos un campo sea proporcionado para actualizar.
        """
        if self.title is None and self.content is None:
            raise ValueError('Debe proporcionar al menos un campo para actualizar')
        return self


# ============================================
# Modelos para Respuesta
# ============================================

class Note(NoteBase):
    """
    Modelo completo de nota para respuestas API.
    Incluye todos los campos con sus validaciones.
    """
    id: int = Field(
        ...,
        description="ID único de la nota",
        examples=[1, 2, 3]
    )
    created_at: datetime = Field(
        ...,
        description="Fecha y hora de creación",
        examples=["2024-01-15T10:30:00Z"]
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Fecha y hora de última actualización",
        examples=["2024-01-15T11:45:00Z"]
    )
    
    # Configuración usando Pydantic V2
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Mi primera nota",
                "content": "Este es el contenido de mi nota personal.",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T11:45:00Z"
            }
        }
    )


# ============================================
# Modelos para Listas y Respuestas Paginadas
# ============================================

class NoteListResponse(BaseModel):
    """
    Modelo para respuestas paginadas de lista de notas.
    """
    items: List[Note] = Field(
        ...,
        description="Lista de notas en la página actual"
    )
    total: int = Field(
        ...,
        description="Número total de notas",
        examples=[100]
    )
    page: int = Field(
        ...,
        description="Número de página actual",
        examples=[1]
    )
    size: int = Field(
        ...,
        description="Tamaño de página",
        examples=[10]
    )
    pages: int = Field(
        ...,
        description="Número total de páginas",
        examples=[10]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": 1,
                        "title": "Nota 1",
                        "content": "Contenido 1",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": None
                    }
                ],
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }
        }
    )


# ============================================
# Modelos para Estadísticas
# ============================================

class NoteStats(BaseModel):
    """
    Modelo para estadísticas de notas.
    """
    total_notes: int = Field(
        ...,
        description="Número total de notas",
        examples=[150]
    )
    average_content_length: float = Field(
        ...,
        description="Longitud promedio del contenido",
        examples=[245.75]
    )
    last_updated: Optional[datetime] = Field(
        None,
        description="Fecha de la última actualización",
        examples=["2024-01-15T11:45:00Z"]
    )
    notes_without_updates: int = Field(
        ...,
        description="Número de notas nunca actualizadas",
        examples=[25]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_notes": 150,
                "average_content_length": 245.75,
                "last_updated": "2024-01-15T11:45:00Z",
                "notes_without_updates": 25
            }
        }
    )


# ============================================
# Modelos para Búsqueda
# ============================================

class NoteSearchParams(BaseModel):
    """
    Modelo para parámetros de búsqueda de notas.
    """
    query: Optional[str] = Field(
        None,
        description="Término de búsqueda",
        examples=["importante"]
    )
    skip: int = Field(
        0,
        ge=0,
        description="Número de registros a saltar",
        examples=[0]
    )
    limit: int = Field(
        100,
        ge=1,
        le=1000,
        description="Número máximo de registros",
        examples=[10]
    )
    sort_by: str = Field(
        "created_at",
        pattern="^(created_at|updated_at|title)$",
        description="Campo por el cual ordenar",
        examples=["created_at"]
    )
    sort_order: str = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Dirección del orden",
        examples=["desc"]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "importante",
                "skip": 0,
                "limit": 10,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }
    )