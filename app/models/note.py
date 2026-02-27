from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from app.database.base import Base
import re

class Note(Base):
    __tablename__ = "notes"
    
    # Columnas principales
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)  # Añadido índice para búsquedas rápidas
    content = Column(Text, nullable=False)
    
    # Timestamps con valores por defecto en la BD
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Índices compuestos para consultas comunes
    __table_args__ = (
        Index('idx_notes_created_updated', 'created_at', 'updated_at'),
        Index('idx_notes_title_content', 'title', 'content'),  # Útil para búsquedas de texto
    )
    
    @validates('title')
    def validate_title(self, key, title):
        """
        Valida y limpia el título antes de guardarlo.
        """
        if not title or not title.strip():
            raise ValueError("El título no puede estar vacío")
        
        # Limpiar espacios extras y sanitizar
        title = ' '.join(title.strip().split())
        
        if len(title) > 200:
            raise ValueError("El título no puede exceder los 200 caracteres")
        
        return title
    
    @validates('content')
    def validate_content(self, key, content):
        """
        Valida y limpia el contenido antes de guardarlo.
        """
        if not content or not content.strip():
            raise ValueError("El contenido no puede estar vacío")
        
        # Limpiar espacios extras pero mantener saltos de línea
        content = content.strip()
        
        return content
    
    def to_dict(self):
        """
        Convierte el modelo a diccionario para respuestas personalizadas.
        """
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def update(self, **kwargs):
        """
        Método de utilidad para actualizar múltiples campos.
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ['id', 'created_at']:
                setattr(self, key, value)
    
    def __repr__(self):
        """
        Representación del objeto para debugging.
        """
        return f"<Note(id={self.id}, title='{self.title[:30]}...', created={self.created_at})>"
    
    class Config:
        """
        Metadatos del modelo para SQLAlchemy
        """
        orm_mode = True