from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import or_, and_, func
from typing import List, Optional
import logging
from datetime import datetime

from app.database.connection import get_db
from app.models.note import Note as NoteModel
from app.schemas.note import (
    Note, NoteCreate, NoteUpdate, NoteListResponse, 
    NoteStats, NoteSearchParams
)

# Configuración de logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])

@router.post(
    "/", 
    response_model=Note, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva nota",
    description="Crea una nota con título, contenido, y campos adicionales como etiquetas, favorito, archivado y color."
)
async def create_note(
    note: NoteCreate, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para crear una nueva nota.
    
    - **title**: Título de la nota (requerido, máximo 200 caracteres)
    - **content**: Contenido de la nota (requerido)
    - **is_favorite**: Marcar como favorito (opcional, por defecto false)
    - **is_archived**: Marcar como archivado (opcional, por defecto false)
    - **tags**: Lista de etiquetas (opcional)
    - **color_hex**: Color personalizado en formato #RRGGBB (opcional)
    
    Retorna la nota creada con su ID y timestamps.
    """
    try:
        # Crear instancia del modelo con todos los campos
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
        
        logger.info(f"Nota creada exitosamente: ID {db_note.id}, Tags: {db_note.tags}, Favorita: {db_note.is_favorite}")
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
    description="Obtiene una lista paginada de todas las notas (no eliminadas). Incluye filtros por favoritos, archivados y etiquetas."
)
async def read_notes(
    request: Request,
    response: Response,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    is_favorite: Optional[bool] = None,
    is_archived: Optional[bool] = None,
    tags: Optional[str] = None,  # Formato: "tag1,tag2,tag3"
    db: Session = Depends(get_db)
):
    """
    Endpoint para listar notas con filtros y paginación.
    
    - **skip**: Número de registros a saltar (para paginación)
    - **limit**: Número máximo de registros a retornar
    - **search**: Término de búsqueda en título y contenido (opcional)
    - **sort_by**: Campo por el cual ordenar (created_at, updated_at, title)
    - **sort_order**: Dirección del orden (asc o desc)
    - **is_favorite**: Filtrar por favoritos (opcional)
    - **is_archived**: Filtrar por archivados (opcional)
    - **tags**: Filtrar por etiquetas (separadas por comas)
    """
    try:
        # Construir query base (excluir notas eliminadas)
        query = db.query(NoteModel).filter(NoteModel.deleted_at.is_(None))
        
        # Aplicar búsqueda si se proporciona
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    NoteModel.title.ilike(search_term),
                    NoteModel.content.ilike(search_term)
                )
            )
        
        # Filtrar por favoritos
        if is_favorite is not None:
            query = query.filter(NoteModel.is_favorite == is_favorite)
        
        # Filtrar por archivados
        if is_archived is not None:
            query = query.filter(NoteModel.is_archived == is_archived)
        
        # Filtrar por etiquetas
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if tag_list:
                # Buscar notas que contengan al menos una de las etiquetas
                tag_filters = []
                for tag in tag_list:
                    # PostgreSQL: usar operador de JSON
                    tag_filters.append(NoteModel.tags.contains(tag))
                if tag_filters:
                    query = query.filter(or_(*tag_filters))
        
        # Obtener total de registros (para paginación)
        total_count = query.count()
        
        # Aplicar ordenamiento
        if sort_by in ["created_at", "updated_at", "title", "is_favorite", "is_archived"]:
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
            next_url = str(request.url).split('?')[0]
            params = []
            if search:
                params.append(f"search={search}")
            if is_favorite is not None:
                params.append(f"is_favorite={is_favorite}")
            if is_archived is not None:
                params.append(f"is_archived={is_archived}")
            if tags:
                params.append(f"tags={tags}")
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
        note = db.get(NoteModel, note_id)
        
        if note is None or note.deleted_at is not None:
            logger.warning(f"Nota no encontrada o eliminada: ID {note_id}")
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
    - **is_favorite**: Cambiar estado de favorito (opcional)
    - **is_archived**: Cambiar estado de archivado (opcional)
    - **tags**: Nueva lista de etiquetas (opcional)
    - **color_hex**: Nuevo color (opcional)
    
    Retorna la nota actualizada.
    """
    try:
        # Buscar la nota
        note = db.get(NoteModel, note_id)
        
        if note is None or note.deleted_at is not None:
            logger.warning(f"Intento de actualizar nota inexistente o eliminada: ID {note_id}")
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
        
        # Log de cambios
        logger.info(f"Actualizando nota {note_id} con datos: {update_data}")
        
        # Actualizar campos
        for key, value in update_data.items():
            setattr(note, key, value)
        
        # Actualizar timestamp
        note.updated_at = datetime.now()
        
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
    summary="Eliminar una nota (soft delete)",
    description="Mueve una nota a la papelera (soft delete) en lugar de eliminarla permanentemente."
)
async def delete_note(
    note_id: int, 
    db: Session = Depends(get_db)
):
    """
    Endpoint para eliminar una nota (soft delete).
    
    - **note_id**: ID de la nota a eliminar
    
    La nota se marca como eliminada pero permanece en la base de datos.
    No retorna contenido en caso de éxito (204 No Content).
    """
    try:
        # Buscar la nota
        note = db.get(NoteModel, note_id)
        
        if note is None or note.deleted_at is not None:
            logger.warning(f"Intento de eliminar nota inexistente o ya eliminada: ID {note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        # Soft delete: marcar como eliminada
        note.deleted_at = datetime.now()
        db.commit()
        
        logger.info(f"Nota movida a papelera exitosamente: ID {note_id}")
        return None  # 204 No Content
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error de base de datos al eliminar nota {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al eliminar la nota"
        )

@router.post(
    "/{note_id}/restore",
    response_model=Note,
    summary="Restaurar una nota",
    description="Restaura una nota previamente eliminada (soft delete)."
)
async def restore_note(
    note_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint para restaurar una nota eliminada.
    
    - **note_id**: ID de la nota a restaurar
    
    Retorna la nota restaurada.
    """
    try:
        # Buscar la nota (incluyendo eliminadas)
        note = db.get(NoteModel, note_id)
        
        if note is None:
            logger.warning(f"Intento de restaurar nota inexistente: ID {note_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        if note.deleted_at is None:
            logger.warning(f"Intento de restaurar nota no eliminada: ID {note_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nota no está eliminada"
            )
        
        # Restaurar
        note.deleted_at = None
        db.commit()
        db.refresh(note)
        
        logger.info(f"Nota restaurada exitosamente: ID {note_id}")
        return note
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error de base de datos al restaurar nota {note_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al restaurar la nota"
        )

@router.get(
    "/deleted/all",
    response_model=List[Note],
    summary="Listar notas eliminadas",
    description="Obtiene una lista de todas las notas en la papelera (soft delete)."
)
async def read_deleted_notes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Endpoint para listar notas eliminadas (papelera).
    
    - **skip**: Número de registros a saltar
    - **limit**: Número máximo de registros a retornar
    
    Retorna lista de notas eliminadas.
    """
    try:
        notes = db.query(NoteModel).filter(
            NoteModel.deleted_at.isnot(None)
        ).offset(skip).limit(limit).all()
        
        logger.debug(f"Notas eliminadas listadas: {len(notes)}")
        return notes
        
    except SQLAlchemyError as e:
        logger.error(f"Error al listar notas eliminadas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener notas eliminadas"
        )

@router.get(
    "/stats/summary",
    response_model=NoteStats,
    summary="Estadísticas completas de notas",
    description="Obtiene estadísticas detalladas de las notas incluyendo favoritos, archivados y etiquetas populares."
)
async def get_notes_stats(
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener estadísticas completas de las notas.
    
    Retorna:
    - total_notes: Número total de notas activas
    - total_favorites: Número de notas favoritas
    - total_archived: Número de notas archivadas
    - average_content_length: Longitud promedio del contenido
    - most_used_tags: Etiquetas más utilizadas con sus contadores
    - last_updated: Fecha de la última actualización
    - notes_without_updates: Notas nunca actualizadas
    """
    try:
        # Notas activas (no eliminadas)
        active_notes = db.query(NoteModel).filter(NoteModel.deleted_at.is_(None))
        
        # Estadísticas básicas
        total_notes = active_notes.count()
        total_favorites = active_notes.filter(NoteModel.is_favorite == True).count()
        total_archived = active_notes.filter(NoteModel.is_archived == True).count()
        
        # Longitud promedio del contenido
        avg_length = db.query(
            func.avg(func.length(NoteModel.content))
        ).filter(NoteModel.deleted_at.is_(None)).scalar() or 0
        
        # Última actualización
        last_updated = db.query(
            func.max(NoteModel.updated_at)
        ).filter(NoteModel.deleted_at.is_(None)).scalar()
        
        # Notas sin actualizaciones (created_at == updated_at)
        notes_without_updates = active_notes.filter(
            NoteModel.created_at == NoteModel.updated_at
        ).count()
        
        # Etiquetas más utilizadas
        all_notes = active_notes.all()
        tag_counter = {}
        for note in all_notes:
            if note.tags:
                for tag in note.tags:
                    tag_counter[tag] = tag_counter.get(tag, 0) + 1
        
        # Ordenar y tomar top 10
        most_used_tags = [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        result = NoteStats(
            total_notes=total_notes,
            total_favorites=total_favorites,
            total_archived=total_archived,
            average_content_length=round(float(avg_length), 2),
            most_used_tags=most_used_tags,
            last_updated=last_updated.isoformat() if last_updated else None,
            notes_without_updates=notes_without_updates
        )
        
        logger.debug(f"Estadísticas calculadas: {result}")
        return result
        
    except SQLAlchemyError as e:
        logger.error(f"Error al calcular estadísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener estadísticas"
        )

@router.post(
    "/{note_id}/toggle-favorite",
    response_model=Note,
    summary="Alternar favorito",
    description="Cambia el estado de favorito de una nota."
)
async def toggle_favorite(
    note_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint para alternar el estado de favorito de una nota.
    
    - **note_id**: ID de la nota
    
    Retorna la nota con el estado actualizado.
    """
    try:
        note = db.get(NoteModel, note_id)
        
        if note is None or note.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        note.toggle_favorite()
        note.updated_at = datetime.now()
        db.commit()
        db.refresh(note)
        
        logger.info(f"Estado favorito alternado para nota {note_id}: {note.is_favorite}")
        return note
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al alternar favorito: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al alternar favorito"
        )

@router.post(
    "/{note_id}/toggle-archived",
    response_model=Note,
    summary="Alternar archivado",
    description="Cambia el estado de archivado de una nota."
)
async def toggle_archived(
    note_id: int,
    db: Session = Depends(get_db)
):
    """
    Endpoint para alternar el estado de archivado de una nota.
    
    - **note_id**: ID de la nota
    
    Retorna la nota con el estado actualizado.
    """
    try:
        note = db.get(NoteModel, note_id)
        
        if note is None or note.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nota con ID {note_id} no encontrada"
            )
        
        note.toggle_archived()
        note.updated_at = datetime.now()
        db.commit()
        db.refresh(note)
        
        logger.info(f"Estado archivado alternado para nota {note_id}: {note.is_archived}")
        return note
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al alternar archivado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al alternar archivado"
        )