from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.api.appointments import get_visible, role_code
from backend.api.auth import require_roles
from backend.core.database import get_db
from backend.core.models import Attachment, Diagnostic, User, WorkOrder
from backend.api.work_orders import get_visible as get_visible_order
from backend.logic.files_logic import AttachmentOut, list_attachments, prepare_files, store_files

router = APIRouter(tags=["files"])

INLINE_OK = {"image/png", "image/jpeg", "application/pdf"}


def get_diagnostic_or_404(db: Session, diagnostic_id: int) -> Diagnostic:
    diagnostic = db.get(Diagnostic, diagnostic_id)
    if diagnostic is None:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    return diagnostic


def check_access(db: Session, att: Attachment, user: User):
    if att.work_order_id is not None:
        get_visible_order(db, att.work_order_id, user)
    else:
        diagnostic = get_diagnostic_or_404(db, att.diagnostic_id)
        get_visible(db, diagnostic.appointment_id, user)

@router.post("/work-orders/{order_id}/files", response_model=List[AttachmentOut], status_code=201)
def upload_order_files(order_id: int, files: List[UploadFile] = File(...),
                       user: User = Depends(require_roles("admin")),
                       db: Session = Depends(get_db)):
    order = db.get(WorkOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ-наряд не найден")
    saved = store_files(db, prepare_files(files), user.id, work_order_id=order.id)
    db.commit()
    return [AttachmentOut.model_validate(a) for a in saved]


@router.get("/work-orders/{order_id}/files", response_model=List[AttachmentOut])
def list_order_files(order_id: int,
                     user: User = Depends(require_roles("client", "master", "admin")),
                     db: Session = Depends(get_db)):
    order = get_visible_order(db, order_id, user)
    return list_attachments(db, work_order_id=order.id)


@router.post("/diagnostics/{diagnostic_id}/files", response_model=List[AttachmentOut],
             status_code=201)
def upload_diagnostic_files(diagnostic_id: int, files: List[UploadFile] = File(...),
                            user: User = Depends(require_roles("master", "admin")),
                            db: Session = Depends(get_db)):
    diagnostic = get_diagnostic_or_404(db, diagnostic_id)
    if role_code(user, db) == "master" and diagnostic.master_user_id != user.id:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    saved = store_files(db, prepare_files(files), user.id, diagnostic_id=diagnostic.id)
    db.commit()
    return [AttachmentOut.model_validate(a) for a in saved]


@router.get("/diagnostics/{diagnostic_id}/files", response_model=List[AttachmentOut])
def list_diagnostic_files(diagnostic_id: int,
                          user: User = Depends(require_roles("client", "master", "admin")),
                          db: Session = Depends(get_db)):
    diagnostic = get_diagnostic_or_404(db, diagnostic_id)
    get_visible(db, diagnostic.appointment_id, user)
    return list_attachments(db, diagnostic_id=diagnostic.id)


@router.get("/files/{file_id}")
def download_file(file_id: int, inline: bool = False,
                  user: User = Depends(require_roles("client", "master", "admin")),
                  db: Session = Depends(get_db)):
    att = db.get(Attachment, file_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    check_access(db, att, user)
    mode = "inline" if inline and att.content_type in INLINE_OK else "attachment"
    return Response(
        content=att.data,
        media_type=att.content_type,
        headers={
            "Content-Disposition": "%s; filename*=UTF-8''%s" % (mode, quote(att.filename)),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/files/{file_id}", status_code=204)
def delete_file(file_id: int, user: User = Depends(require_roles("master", "admin")),
                db: Session = Depends(get_db)):
    att = db.get(Attachment, file_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    check_access(db, att, user)
    if role_code(user, db) == "master" and att.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="Мастер может удалять только свои файлы")
    db.delete(att)
    db.commit()