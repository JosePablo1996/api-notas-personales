from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Boolean, JSON
from sqlalchemy.sql import func

# Creamos la clase base para todos los modelos
Base = declarative_base()

# Clase base opcional con campos comunes (si quieres usarla en otros modelos)
class BaseModel(Base):
    __abstract__ = True  # Esta clase no creará una tabla en la BD
    
    # Timestamps estándar
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Para soft delete
    
    # Campos comunes para todas las notas (si se hereda)
    is_favorite = Column(Boolean, default=False, nullable=False, server_default='0')
    is_archived = Column(Boolean, default=False, nullable=False, server_default='0')
    tags = Column(JSON, default=list, nullable=False, server_default='[]')
    
    def soft_delete(self):
        """Marca el registro como eliminado"""
        self.deleted_at = func.now()
    
    def restore(self):
        """Restaura un registro eliminado"""
        self.deleted_at = None
    
    def toggle_favorite(self):
        """Cambia el estado de favorito"""
        self.is_favorite = not self.is_favorite
    
    def toggle_archived(self):
        """Cambia el estado de archivado"""
        self.is_archived = not self.is_archived
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        result = {
            'id': self.id if hasattr(self, 'id') else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'is_favorite': self.is_favorite,
            'is_archived': self.is_archived,
            'tags': self.tags,
        }
        
        # Agregar otros atributos específicos si existen
        if hasattr(self, 'title'):
            result['title'] = self.title
        if hasattr(self, 'content'):
            result['content'] = self.content
        if hasattr(self, 'color_hex'):
            result['color_hex'] = self.color_hex
            
        return result
    
    def __repr__(self):
        """Representación del objeto para debugging"""
        status = []
        if hasattr(self, 'is_favorite') and self.is_favorite:
            status.append("⭐")
        if hasattr(self, 'is_archived') and self.is_archived:
            status.append("📦")
        if self.deleted_at:
            status.append("🗑️")
        
        status_str = f" [{''.join(status)}]" if status else ""
        
        if hasattr(self, 'title'):
            return f"<{self.__class__.__name__}(id={self.id}, title='{self.title[:30]}...'{status_str})>"
        else:
            return f"<{self.__class__.__name__}(id={self.id}{status_str})>"