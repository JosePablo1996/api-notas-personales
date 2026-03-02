from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from app.database.base import Base
import re
from datetime import datetime

class Note(Base):
    __tablename__ = "notes"
    
    # Columnas principales
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    
    # 👇 NUEVOS CAMPOS
    is_favorite = Column(Boolean, default=False, nullable=False, server_default='0')
    is_archived = Column(Boolean, default=False, nullable=False, server_default='0')
    tags = Column(JSON, default=list, nullable=False, server_default='[]')
    color_hex = Column(String(7), nullable=True)  # Formato #RRGGBB
    
    # Timestamps
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
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Índices compuestos para consultas comunes
    __table_args__ = (
        Index('idx_notes_created_updated', 'created_at', 'updated_at'),
        Index('idx_notes_title_content', 'title', 'content'),
        Index('idx_notes_favorite', 'is_favorite'),  # 👈 NUEVO ÍNDICE
        Index('idx_notes_archived', 'is_archived'),  # 👈 NUEVO ÍNDICE
        Index('idx_notes_deleted', 'deleted_at'),    # 👈 NUEVO ÍNDICE
    )
    
    @validates('title')
    def validate_title(self, key, title):
        """
        Valida y limpia el título antes de guardarlo.
        """
        if not title or not title.strip():
            raise ValueError("El título no puede estar vacío")
        
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
        
        content = content.strip()
        
        return content
    
    @validates('color_hex')
    def validate_color_hex(self, key, color_hex):
        """
        Valida que el color esté en formato hexadecimal #RRGGBB
        """
        if color_hex is None:
            return None
        
        # Patrón para validar color hexadecimal
        pattern = r'^#([A-Fa-f0-9]{6})$'
        if not re.match(pattern, color_hex):
            raise ValueError("El color debe estar en formato hexadecimal #RRGGBB")
        
        return color_hex
    
    @validates('tags')
    def validate_tags(self, key, tags):
        """
        Valida que los tags sean una lista de strings
        """
        if tags is None:
            return []
        
        if not isinstance(tags, list):
            raise ValueError("Los tags deben ser una lista")
        
        # Limpiar cada tag
        clean_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:  # Máximo 50 caracteres por tag
                clean_tags.append(tag)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_tags = []
        for tag in clean_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def soft_delete(self):
        """
        Marca la nota como eliminada (soft delete)
        """
        self.deleted_at = datetime.now()
    
    def restore(self):
        """
        Restaura una nota eliminada
        """
        self.deleted_at = None
    
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
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'is_favorite': self.is_favorite,
            'is_archived': self.is_archived,
            'tags': self.tags,
            'color_hex': self.color_hex,
        }
    
    def update(self, **kwargs):
        """
        Método de utilidad para actualizar múltiples campos.
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ['id', 'created_at']:
                setattr(self, key, value)
    
    def toggle_favorite(self):
        """
        Cambia el estado de favorito
        """
        self.is_favorite = not self.is_favorite
    
    def toggle_archived(self):
        """
        Cambia el estado de archivado
        """
        self.is_archived = not self.is_archived
    
    def add_tag(self, tag):
        """
        Agrega un tag a la lista
        """
        if not tag or not isinstance(tag, str):
            return
        
        clean_tag = tag.strip().lower()
        if not clean_tag or len(clean_tag) > 50:
            return
        
        current_tags = list(self.tags) if self.tags else []
        if clean_tag not in current_tags:
            current_tags.append(clean_tag)
            self.tags = current_tags
    
    def remove_tag(self, tag):
        """
        Elimina un tag de la lista
        """
        if not tag or not isinstance(tag, str):
            return
        
        clean_tag = tag.strip().lower()
        current_tags = list(self.tags) if self.tags else []
        if clean_tag in current_tags:
            current_tags.remove(clean_tag)
            self.tags = current_tags
    
    def __repr__(self):
        """
        Representación del objeto para debugging.
        """
        status = []
        if self.is_favorite:
            status.append("⭐")
        if self.is_archived:
            status.append("📦")
        if self.deleted_at:
            status.append("🗑️")
        
        status_str = f" [{''.join(status)}]" if status else ""
        
        tags_str = f" tags={self.tags}" if self.tags else ""
        
        return f"<Note(id={self.id}, title='{self.title[:30]}...'{status_str}{tags_str}, created={self.created_at})>"
    
    class Config:
        """
        Metadatos del modelo para SQLAlchemy
        """
        orm_mode = True