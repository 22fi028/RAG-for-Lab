# [ROLE] 文書アップロード・一覧・削除・インデックス状況確認・OCR詳細／補正テキスト／再インデックス・元画像配信・チャンク抜粋取得のAPIエンドポイント
# [DEPS] models/db.py, services/pipeline.py, services/rag.py, core/config.py
# [CALLED_BY] main.py

import os
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

import chromadb
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db import Document, OcrResult, get_db
from app.services.pipeline import run_indexing_pipeline, sort_blocks
from app.services.rag import invalidate_bm25_cache


async def _run_pipeline_and_invalidate(doc_id: str) -> None:
    """インデックス化パイプライン完了後にBM25キャッシュを破棄する。"""
    try:
        await run_indexing_pipeline(doc_id)
    finally:
        invalidate_bm25_cache()


router = APIRouter()


ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".png", ".jpg", ".jpeg"}

EXT_TO_SOURCE_TYPE = {
    ".pdf": "pdf",
    ".pptx": "pptx",
    ".docx": "word",
    ".png": "ocr",
    ".jpg": "ocr",
    ".jpeg": "ocr",
}

UPLOAD_ROOT = Path("/data/raw")


class DocumentOut(BaseModel):
    id: UUID
    title: Optional[str]
    author: Optional[str]
    year: Optional[int]
    source_type: str
    file_path: Optional[str]
    chunk_count: int
    status: str
    error_message: Optional[str]
    avg_confidence: Optional[float]
    is_corrected: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentStatusOut(BaseModel):
    id: UUID
    status: str
    chunk_count: int
    error_message: Optional[str]


class DocumentUploadAccepted(BaseModel):
    id: UUID
    status: str


class OcrBlockOut(BaseModel):
    text: str
    confidence: float
    bbox: List[float]


class OcrDetailOut(BaseModel):
    avg_confidence: float
    low_conf_count: int
    blocks: List[OcrBlockOut]


class OcrTextOut(BaseModel):
    text: str
    is_corrected: bool


class OcrTextIn(BaseModel):
    text: str


class ReindexAccepted(BaseModel):
    status: str


class ChunkExcerptOut(BaseModel):
    content: str


@router.get("/documents", response_model=List[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    rows = (
        db.query(Document, OcrResult.avg_confidence, OcrResult.corrected_text)
        .outerjoin(OcrResult, OcrResult.document_id == Document.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        DocumentOut(
            id=doc.id,
            title=doc.title,
            author=doc.author,
            year=doc.year,
            source_type=doc.source_type,
            file_path=doc.file_path,
            chunk_count=doc.chunk_count,
            status=doc.status,
            error_message=doc.error_message,
            avg_confidence=avg_confidence,
            is_corrected=corrected_text is not None,
            created_at=doc.created_at,
        )
        for doc, avg_confidence, corrected_text in rows
    ]


@router.get("/documents/chunk-excerpt", response_model=ChunkExcerptOut)
def get_chunk_excerpt(title: str, chapter: str = "", page: int = 0):
    """
    title / chapter / page をキーに ChromaDB を検索し、最初にマッチしたチャンクの
    先頭 settings.rag_excerpt_max_length 文字を返す。マッチなしは content="" を返す（404にしない）。
    chapter / page は ChromaDB の where 句では絞らず Python 側でフィルタする
    （ChromaDB の where は AND 条件の組み合わせで複雑になりやすいため）。
    """
    try:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_or_create_collection(settings.chroma_collection)
        results = collection.get(
            where={"title": title},
            include=["documents", "metadatas"],
        )
    except Exception as e:
        print(f"[chunk-excerpt] ChromaDB get failed: {e}")
        return ChunkExcerptOut(content="")

    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    for doc, meta in zip(documents, metadatas):
        meta = meta or {}
        if chapter and (meta.get("chapter") or "") != chapter:
            continue
        if page and int(meta.get("page_num") or 0) != page:
            continue
        text = doc or ""
        return ChunkExcerptOut(content=text[: settings.rag_excerpt_max_length])
    return ChunkExcerptOut(content="")


@router.get("/documents/{doc_id}/status", response_model=DocumentStatusOut)
def get_document_status(doc_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusOut(
        id=doc.id,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.get("/documents/{doc_id}/image")
def get_document_image(doc_id: UUID, db: Session = Depends(get_db)):
    """OCR文書の元画像を返す。OCR以外・ファイル不存在は 404。"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.source_type != "ocr":
        raise HTTPException(status_code=404, detail="Image not available for this document type")
    if not doc.file_path:
        raise HTTPException(status_code=404, detail="File path not recorded")

    # パストラバーサル防止: 解決後も UPLOAD_ROOT 配下であることを確認する
    file_path = Path(doc.file_path).resolve()
    try:
        file_path.relative_to(UPLOAD_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    ext = file_path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(ext, "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=file_path.name)


@router.get("/documents/{doc_id}/ocr", response_model=OcrDetailOut)
def get_document_ocr(doc_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.source_type != "ocr":
        raise HTTPException(status_code=404, detail="OCR detail not available for this document type")

    ocr = db.query(OcrResult).filter(OcrResult.document_id == doc_id).first()
    if not ocr:
        raise HTTPException(status_code=404, detail="OCR result not found")

    return OcrDetailOut(
        avg_confidence=ocr.avg_confidence,
        low_conf_count=ocr.low_conf_count,
        blocks=ocr.blocks or [],
    )


@router.get("/documents/{doc_id}/ocr/text", response_model=OcrTextOut)
def get_document_ocr_text(doc_id: UUID, db: Session = Depends(get_db)):
    """補正テキストがあれば優先して返す。なければ blocks の text を改行で結合して返す。"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.source_type != "ocr":
        raise HTTPException(status_code=404, detail="OCR text not available for this document type")

    ocr = db.query(OcrResult).filter(OcrResult.document_id == doc_id).first()
    if not ocr:
        raise HTTPException(status_code=404, detail="OCR result not found")

    if ocr.corrected_text:
        return OcrTextOut(text=ocr.corrected_text, is_corrected=True)

    blocks = sort_blocks(ocr.blocks or [])

    # _row_id を付与して同一行をグループ化
    from app.services.pipeline import OCR_ROW_GAP_THRESHOLD
    row_id = 0
    prev_ymin = blocks[0]["bbox"][1] if blocks else 0
    for block in blocks:
        ymin = block["bbox"][1]
        if ymin - prev_ymin > OCR_ROW_GAP_THRESHOLD:
            row_id += 1
        block["_row_id"] = row_id
        prev_ymin = ymin

    # 同一行はスペース結合・行間は改行
    from itertools import groupby
    lines = []
    for _, group in groupby(blocks, key=lambda b: b["_row_id"]):
        line = " ".join(b.get("text", "") for b in group)
        lines.append(line)

    # 一時キーを削除
    for block in blocks:
        block.pop("_row_id", None)

    text = "\n".join(lines)
    return OcrTextOut(text=text, is_corrected=False)


@router.put("/documents/{doc_id}/ocr/text")
def put_document_ocr_text(
    doc_id: UUID, body: OcrTextIn, db: Session = Depends(get_db)
):
    """補正テキストを保存する。空文字を渡せば NULL に戻し未補正状態とする。"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.source_type != "ocr":
        raise HTTPException(status_code=404, detail="OCR text not available for this document type")

    ocr = db.query(OcrResult).filter(OcrResult.document_id == doc_id).first()
    if not ocr:
        raise HTTPException(status_code=404, detail="OCR result not found")

    ocr.corrected_text = body.text if body.text else None
    db.commit()
    return {"status": "saved"}


@router.post(
    "/documents/{doc_id}/reindex",
    response_model=ReindexAccepted,
    status_code=202,
)
async def reindex_document(
    doc_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """ChromaDB の既存チャンクを削除した後、status=pending に戻して再インデックスを実行する。"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Step 1: ChromaDB から既存チャンクを削除（最大2回リトライ・指数バックオフ）
    for attempt in range(2):
        try:
            client = chromadb.PersistentClient(path=settings.chroma_path)
            collection = client.get_or_create_collection(settings.chroma_collection)
            results = collection.get(where={"doc_id": str(doc_id)})
            if results["ids"]:
                collection.delete(ids=results["ids"])
            break
        except Exception as e:
            if attempt == 1:
                print(f"ChromaDB delete failed after 2 attempts: {e}")
            else:
                await asyncio.sleep(1.0)

    # Step 2: status を pending に戻す（チャンク数・エラーもリセット）
    doc.status = "pending"
    doc.chunk_count = 0
    doc.error_message = None
    db.commit()

    # Step 3: バックグラウンドで再インデックス
    background_tasks.add_task(_run_pipeline_and_invalidate, str(doc.id))

    return ReindexAccepted(status="reindexing")


@router.post("/documents", response_model=DocumentUploadAccepted, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    doc_id = uuid4()
    save_dir = UPLOAD_ROOT / str(doc_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = Document(
        id=doc_id,
        title=Path(filename).stem,
        source_type=EXT_TO_SOURCE_TYPE[ext],
        file_path=str(save_path),
        chunk_count=0,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_run_pipeline_and_invalidate, str(doc.id))

    return DocumentUploadAccepted(id=doc.id, status=doc.status)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Step 1: ChromaDB から削除（最大2回リトライ・指数バックオフ）
    for attempt in range(2):
        try:
            client = chromadb.PersistentClient(path=settings.chroma_path)
            collection = client.get_or_create_collection(settings.chroma_collection)
            results = collection.get(where={"doc_id": str(doc_id)})
            if results["ids"]:
                collection.delete(ids=results["ids"])
            break
        except Exception as e:
            if attempt == 1:
                print(f"ChromaDB delete failed after 2 attempts: {e}")
            else:
                await asyncio.sleep(1.0)

    # Step 2: アップロードファイルを削除
    if doc.file_path and os.path.exists(doc.file_path):
        shutil.rmtree(os.path.dirname(doc.file_path), ignore_errors=True)

    # Step 3: PostgreSQL レコードを削除
    db.delete(doc)
    db.commit()

    # Step 4: BM25 キャッシュを破棄（次回検索時にリビルド）
    invalidate_bm25_cache()
