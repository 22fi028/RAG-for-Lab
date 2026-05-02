# [ROLE] SQLAlchemy モデル定義（conversations / messages / documents / ocr_results テーブル）と DB セッション管理
# [DEPS] core/config.py
# [CALLED_BY] main.py, routers/chat.py, routers/conversations.py, routers/documents.py, services/pipeline.py

import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    CheckConstraint,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.core.config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="messages_role_check"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=True)
    author = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    source_type = Column(Text, nullable=False)
    file_path = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    status = Column(Text, nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    avg_confidence = Column(Float, nullable=False)
    low_conf_count = Column(Integer, nullable=False)
    # blocks: [{"text": "...", "confidence": 0.95, "bbox": [x1, y1, x2, y2]}, ...]
    blocks = Column(JSONB, nullable=False)
    # NULL なら未補正。値が入っていれば再インデックス時に blocks より優先する。
    corrected_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def apply_lightweight_migrations() -> None:
    """create_all は新規カラムを追加しないため、既存テーブルへの ADD COLUMN を冪等に実行する。"""
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE ocr_results ADD COLUMN IF NOT EXISTS corrected_text TEXT")
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
