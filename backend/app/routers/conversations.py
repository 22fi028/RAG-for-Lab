# [ROLE] 会話セッションのCRUD APIエンドポイント
# [DEPS] models/db.py, core/config.py
# [CALLED_BY] main.py

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import Conversation, Message, get_db


router = APIRouter()


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationOut(BaseModel):
    id: UUID
    title: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    sources: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(BaseModel):
    id: UUID
    title: Optional[str]
    created_at: datetime
    messages: List[MessageOut]

    class Config:
        from_attributes = True


@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    return (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    conv = Conversation(title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
