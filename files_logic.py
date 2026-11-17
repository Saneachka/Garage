import io
import os
import zipfile
from typing import List, Optional, Tuple
from datetime import datetime

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Attachment

MAX_SIZE = 50 * 1024 * 1024 
MAX_FILES = 10               

TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size: int
    uploaded_by: int
    created_at: datetime
    work_order_id: Optional[int]
    diagnostic_id: Optional[int]


def _content_ok(ext: str, data: bytes) -> bool:
    if ext == ".pdf":
        return data.startswith(b"%PDF")
    if ext == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                return "word/document.xml" in z.namelist()
        except zipfile.BadZipFile:
            return False
    if ext == ".txt":
        return b"\x00" not in data
    return False


def prepare_files(files: Optional[List[UploadFile]]) -> List[Tuple[str, str, bytes]]:
    """Читает и проверяет все файлы"""
    result = []
    for f in files or []:
        if not f.filename:  # Swagger иногда шлёт пустое поле
            continue
        name = os.path.basename(f.filename.replace("\\", "/")).strip()[:255]
        ext = os.path.splitext(name)[1].lower()
        if not name or ext not in TYPES:
            raise HTTPException(status_code=422,
                                detail="Файл «%s»: разрешены pdf, txt, docx, png, jpeg" % f.filename)
        data = f.file.read(MAX_SIZE + 1)
        if len(data) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="Файл «%s» больше 50 МБ" % name)
        if not data:
            raise HTTPException(status_code=422, detail="Файл «%s» пустой" % name)
        if not _content_ok(ext, data):
            raise HTTPException(status_code=422,
                                detail="Содержимое файла «%s» не соответствует его типу" % name)
        result.append((name, TYPES[ext], data))
    if len(result) > MAX_FILES:
        raise HTTPException(status_code=409, detail="Не более %d файлов" % MAX_FILES)
    return result


def store_files(db: Session, parsed, user_id: int, work_order_id: Optional[int] = None,
                diagnostic_id: Optional[int] = None) -> List[Attachment]:
    """Сохраняет проверенные файлыы"""
    query = select(func.count(Attachment.id))
    if work_order_id is not None:
        query = query.where(Attachment.work_order_id == work_order_id)
    else:
        query = query.where(Attachment.diagnostic_id == diagnostic_id)
    existing = db.scalar(query)
    if existing + len(parsed) > MAX_FILES:
        raise HTTPException(
            status_code=409,
            detail="Не более %d файлов (уже загружено %d)" % (MAX_FILES, existing))
    saved = []
    for name, content_type, data in parsed:
        att = Attachment(work_order_id=work_order_id, diagnostic_id=diagnostic_id,
                         filename=name, content_type=content_type, size=len(data),
                         data=data, uploaded_by=user_id)
        db.add(att)
        saved.append(att)
    db.flush()
    return saved


def list_attachments(db: Session, work_order_id: Optional[int] = None,
                     diagnostic_id: Optional[int] = None) -> List[Attachment]:
    query = select(Attachment)
    if work_order_id is not None:
        query = query.where(Attachment.work_order_id == work_order_id)
    else:
        query = query.where(Attachment.diagnostic_id == diagnostic_id)
    return db.scalars(query.order_by(Attachment.id)).all()