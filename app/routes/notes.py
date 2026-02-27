from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_
from typing import List, Optional
import logging

from app.database.connection import get_db
from app.models.note import Note as NoteModel
from app.schemas.note import Note, NoteCreate, NoteUpdate, NoteListResponse

# Configuración de logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])

@router.post(
    "/", 
    response_model=Note, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva nota",
    description="Crea una nota con título y contenido. El título no puede exceder 200 caracteres."
)
async def create_note(
    note: NoteCreate, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para crear una nueva nota.
    
    - **title**: Título de la nota (requerido, máximo 200 caracteres)
    - **content**: Contenido de la nota (requerido)
    
    Retorna la nota creada con su ID y timestamps.
    """
    try:
        # Crear instancia del modelo
        db_note = NoteModel(**note.model_dump())
        
        # Validaciones adicionales si es necesario
        if len(note.title) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El título debe tener al menos 3 caracteres"
            )
        
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        
        logger.info(f"Nota creada exitosamente: ID {db_note.id}")
        return db_note
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error de integridad al crear nota: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en los datos"
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error de base de datos al crear nota: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al crear la nota"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado al crear nota: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.get(
    "/",
    response_model=List[Note],
    summary="Listar todas las notas",
    description="Obtiene una lista paginada de todas las notas. Incluye headers de paginación."
)
async def read_notes(
    request: Request,
    response: Response,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    """
    Endpoint para listar notas con filtros y paginación.
    
    - **skip**: Número de registros a saltar (para paginación)
    - **limit**: Número máximo de registros a retornar
    - **search**: Término de búsqueda en título y contenido (opcional)
    - **sort_by**: Campo por el cual ordenar (created_at, updated_at, title)
    - **sort_order**: Dirección del orden (asc o desc)
    """
    try:
        # Construir query base
        query = db.query(NoteModel)
        
        # Aplicar búsqueda si se proporciona
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    NoteModel.title.ilike(search_term),
                    NoteModel.content.ilike(search_term)
                )
            )
        
        # Obtener total de registros (para paginación)
        total_count = query.count()
        
        # Aplicar ordenamiento
        if sort_by in ["created_at", "updated_at", "title"]:
            order_column = getattr(NoteModel, sort_by)
            if sort_order == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        else:
            # Orden por defecto
            query = query.order_by(NoteModel.created_at.desc())
        
        # Aplicar paginación
        notes = query.offset(skip).limit(limit).all()
        
        # Configurar headers de paginación
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Page-Size"] = str(limit)
        response.headers["X-Current-Offset"] = str(skip)
        
        # Calcular y añadir URL de siguiente página si existe
        if skip + limit < total_count:
            next_url = str(request.url).split('?')[0]  # Base URL
            params = []
            if search:
                params.append(f"search={search}")
            params.append(f"skip={skip + limit}")
            params.append(f"limit={limit}")
            if sort_by:
                params.append(f"sort_by={sort_by}")
            if sort_order:
                params.append(f"sort_order={sort_order}")
            
            next_url += "?" + "&".join(params)
            response.headers["X-Next-Page"] = next_url
        
        logger.debug(f"Notas listadas: {len(notes)} registros (total: {total_count})")
        return notes
        
    except SQLAlchemyError as e:
        logger.error(f"Error al listar notas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener las notas"
        )

@router.get(
    "/{note_id}",
    response_model=Note,
    summary="Obtener una nota por ID",
    description="Retorna los detalles de una nota específica por su ID."
)
async def read_note(
    note_id: int, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener una nota específica por su ID.
    
    - **note_id**: ID de la nota a buscar
    
    Retorna la nota si existe, o error 404 si no se encuentra.
    """
    try:
        # Usar get() en lugar de filter() para mejor rendimiento
        note = db.get(NoteModel, note_id)
        
        if note is None:
            logger.warning(f"Nota no encontrada: ID {note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        logger.debug(f"Nota recuperada: ID {note_id}")
        return note
        
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener nota {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener la nota"
        )

@router.put(
    "/{note_id}",
    response_model=Note,
    summary="Actualizar una nota",
    description="Actualiza parcial o totalmente una nota existente."
)
async def update_note(
    note_id: int, 
    note_update: NoteUpdate, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para actualizar una nota existente.
    
    - **note_id**: ID de la nota a actualizar
    - **title**: Nuevo título (opcional)
    - **content**: Nuevo contenido (opcional)
    
    Retorna la nota actualizada.
    """
    try:
        # Buscar la nota
        note = db.get(NoteModel, note_id)
        
        if note is None:
            logger.warning(f"Intento de actualizar nota inexistente: ID {note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        # Obtener datos de actualización
        update_data = note_update.model_dump(exclude_unset=True)
        
        # Validar que haya datos para actualizar
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar"
            )
        
        # Validar título si se actualiza
        if 'title' in update_data and len(update_data['title']) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El título debe tener al menos 3 caracteres"
            )
        
        # Actualizar campos
        for key, value in update_data.items():
            setattr(note, key, value)
        
        # Guardar cambios
        db.commit()
        db.refresh(note)
        
        logger.info(f"Nota actualizada exitosamente: ID {note_id}")
        return note
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error de base de datos al actualizar nota {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al actualizar la nota"
        )

@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una nota",
    description="Elimina permanentemente una nota existente."
)
async def delete_note(
    note_id: int, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para eliminar una nota.
    
    - **note_id**: ID de la nota a eliminar
    
    No retorna contenido en caso de éxito (204 No Content).
    """
    try:
        # Buscar la nota
        note = db.get(NoteModel, note_id)
        
        if note is None:
            logger.warning(f"Intento de eliminar nota inexistente: ID {note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        # Eliminar la nota
        db.delete(note)
        db.commit()
        
        logger.info(f"Nota eliminada exitosamente: ID {note_id}")
        return None  # 204 No Content
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error de base de datos al eliminar nota {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar la nota"
        )

@router.get(
    "/stats/summary",
    response_model=dict,
    summary="Estadísticas de notas",
    description="Obtiene estadísticas resumidas de las notas."
)
async def get_notes_stats(
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener estadísticas de las notas.
    
    Retorna:
    - total_notes: Número total de notas
    - average_content_length: Longitud promedio del contenido
    - last_updated: Fecha de la última actualización
    """
    try:
        from sqlalchemy import func
        
        # Obtener estadísticas
        stats = db.query(
            func.count(NoteModel.id).label('total_notes'),
            func.avg(func.length(NoteModel.content)).label('avg_content_length'),
            func.max(NoteModel.updated_at).label('last_updated')
        ).first()
        
        result = {
            "total_notes": stats.total_notes or 0,
            "average_content_length": round(stats.avg_content_length or 0, 2),
            "last_updated": stats.last_updated.isoformat() if stats.last_updated else None
        }
        
        logger.debug(f"Estadísticas calculadas: {result}")
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Error al calcular estadísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )