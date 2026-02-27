from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

# Creamos la clase base para todos los modelos
Base = declarative_base()

# Clase base opcional con campos comunes (si quieres usarla en otros modelos)
class BaseModel(Base):
    __abstract__ = True  # Esta clase no creará una tabla en la BD
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"