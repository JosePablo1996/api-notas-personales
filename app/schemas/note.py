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
    # 👇 NUEVOS CAMPOS
    is_favorite: bool = Field(
        False,
        description="Indica si la nota es favorita",
        examples=[True, False]
    )
    is_archived: bool = Field(
        False,
        description="Indica si la nota está archivada",
        examples=[True, False]
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Lista de etiquetas de la nota",
        examples=[["personal", "trabajo"], ["importante"]]
    )
    color_hex: Optional[str] = Field(
        None,
        description="Color personalizado en formato hexadecimal (#RRGGBB)",
        examples=["#FF5733", "#3366FF"],
        pattern=r'^#([A-Fa-f0-9]{6})$'
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Valida y sanitiza el título."""
        if not v or not v.strip():
            raise ValueError('El título no puede estar vacío')
        
        cleaned = ' '.join(v.strip().split())
        
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Valida y sanitiza el contenido."""
        if not v or not v.strip():
            raise ValueError('El contenido no puede estar vacío')
        
        return v.strip()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Valida y sanitiza la lista de etiquetas."""
        if not v:
            return []
        
        # Limpiar cada etiqueta
        clean_tags = []
        for tag in v:
            if not isinstance(tag, str):
                continue
            tag = tag.strip().lower()
            # Eliminar caracteres especiales y espacios
            tag = re.sub(r'[^\w\s-]', '', tag)
            tag = re.sub(r'[-\s]+', '-', tag)
            if tag and len(tag) <= 50:
                clean_tags.append(tag)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_tags = []
        for tag in clean_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    @field_validator('color_hex')
    @classmethod
    def validate_color_hex(cls, v: Optional[str]) -> Optional[str]:
        """Valida el formato del color hexadecimal."""
        if v is None:
            return v
        
        # Asegurar formato #RRGGBB
        if not re.match(r'^#([A-Fa-f0-9]{6})$', v):
            raise ValueError('El color debe estar en formato hexadecimal #RRGGBB')
        
        return v.upper()
    
    @model_validator(mode='after')
    def check_title_content(self) -> 'NoteBase':
        """Validación a nivel de modelo."""
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
    # 👇 NUEVOS CAMPOS OPCIONALES
    is_favorite: Optional[bool] = Field(
        None,
        description="Cambiar estado de favorito",
        examples=[True, False]
    )
    is_archived: Optional[bool] = Field(
        None,
        description="Cambiar estado de archivado",
        examples=[True, False]
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Lista actualizada de etiquetas",
        examples=[["personal", "trabajo"]]
    )
    color_hex: Optional[str] = Field(
        None,
        description="Color personalizado actualizado",
        examples=["#FF5733"],
        pattern=r'^#([A-Fa-f0-9]{6})$'
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Valida título si se proporciona."""
        if v is not None:
            if not v.strip():
                raise ValueError('El título no puede estar vacío')
            cleaned = ' '.join(v.strip().split())
            return cleaned[0].upper() + cleaned[1:]
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Valida contenido si se proporciona."""
        if v is not None:
            if not v.strip():
                raise ValueError('El contenido no puede estar vacío')
            return v.strip()
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Valida etiquetas si se proporcionan."""
        if v is not None:
            clean_tags = []
            for tag in v:
                if not isinstance(tag, str):
                    continue
                tag = tag.strip().lower()
                tag = re.sub(r'[^\w\s-]', '', tag)
                tag = re.sub(r'[-\s]+', '-', tag)
                if tag and len(tag) <= 50:
                    clean_tags.append(tag)
            
            seen = set()
            unique_tags = []
            for tag in clean_tags:
                if tag not in seen:
                    seen.add(tag)
                    unique_tags.append(tag)
            
            return unique_tags
        return v
    
    @field_validator('color_hex')
    @classmethod
    def validate_color_hex(cls, v: Optional[str]) -> Optional[str]:
        """Valida color hexadecimal si se proporciona."""
        if v is not None:
            if not re.match(r'^#([A-Fa-f0-9]{6})$', v):
                raise ValueError('El color debe estar en formato hexadecimal #RRGGBB')
            return v.upper()
        return v
    
    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'NoteUpdate':
        """Verifica que al menos un campo sea proporcionado."""
        if (self.title is None and self.content is None and 
            self.is_favorite is None and self.is_archived is None and
            self.tags is None and self.color_hex is None):
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
    deleted_at: Optional[datetime] = Field(
        None,
        description="Fecha y hora de eliminación (soft delete)",
        examples=["2024-01-15T12:00:00Z"]
    )
    
    # Configuración usando Pydantic V2
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Mi primera nota",
                "content": "Este es el contenido de mi nota personal.",
                "is_favorite": True,
                "is_archived": False,
                "tags": ["personal", "importante"],
                "color_hex": "#3366FF",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T11:45:00Z",
                "deleted_at": None
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
                        "is_favorite": True,
                        "is_archived": False,
                        "tags": ["personal"],
                        "color_hex": "#3366FF",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": None,
                        "deleted_at": None
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
    total_favorites: int = Field(
        ...,
        description="Número de notas favoritas",
        examples=[25]
    )
    total_archived: int = Field(
        ...,
        description="Número de notas archivadas",
        examples=[10]
    )
    average_content_length: float = Field(
        ...,
        description="Longitud promedio del contenido",
        examples=[245.75]
    )
    most_used_tags: List[dict] = Field(
        ...,
        description="Etiquetas más utilizadas con sus contadores",
        examples=[[{"tag": "personal", "count": 15}, {"tag": "trabajo", "count": 10}]]
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
                "total_favorites": 25,
                "total_archived": 10,
                "average_content_length": 245.75,
                "most_used_tags": [
                    {"tag": "personal", "count": 15},
                    {"tag": "trabajo", "count": 10}
                ],
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
    # 👇 NUEVOS FILTROS
    is_favorite: Optional[bool] = Field(
        None,
        description="Filtrar por favoritos",
        examples=[True]
    )
    is_archived: Optional[bool] = Field(
        None,
        description="Filtrar por archivados",
        examples=[False]
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Filtrar por etiquetas",
        examples=[["personal", "trabajo"]]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "importante",
                "skip": 0,
                "limit": 10,
                "sort_by": "created_at",
                "sort_order": "desc",
                "is_favorite": True,
                "is_archived": False,
                "tags": ["personal"]
            }
        }
    )