from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.connection import get_db
from app.models.note import Note as NoteModel
from app.schemas.note import Note, NoteCreate, NoteUpdate

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])

@router.post("/", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    try:
        db_note = NoteModel(**note.model_dump())
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        return db_note
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Note])
def read_notes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    notes = db.query(NoteModel).offset(skip).limit(limit).all()
    return notes

@router.get("/{note_id}", response_model=Note)
def read_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return note

@router.put("/{note_id}", response_model=Note)
def update_note(note_id: int, note_update: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    for key, value in note_update.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    
    db.commit()
    db.refresh(note)
    return note

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(NoteModel).filter(NoteModel.id == note_id).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    
    db.delete(note)
    db.commit()
    return None