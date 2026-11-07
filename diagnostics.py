from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from appointments import get_visible, role_code
from auth import require_roles
from database import get_db
from models import Appointment, Diagnostic, User

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class DiagnosticIn(BaseModel):
    appointment_id: int
    findings: str = Field(min_length=1, max_length=10000)
    recommended_work: Optional[str] = Field(default=None, max_length=10000)


class DiagnosticUpdate(BaseModel):
    findings: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    recommended_work: Optional[str] = Field(default=None, max_length=10000)


class DiagnosticOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    master_user_id: int
    findings: str
    recommended_work: Optional[str]
    created_at: datetime


@router.post("", response_model=DiagnosticOut, status_code=201)
def create_diagnostic(data: DiagnosticIn, user: User = Depends(require_roles("master")),
                      db: Session = Depends(get_db)):
    # get_visible вернёт 404, если запись не назначена этому мастеру
    appointment = get_visible(db, data.appointment_id, user)
    if appointment.status not in ("confirmed", "completed"):
        raise HTTPException(status_code=409,
                            detail="Диагностику можно внести только по подтверждённой записи")
    if db.scalar(select(Diagnostic.id).where(Diagnostic.appointment_id == appointment.id)):
        raise HTTPException(status_code=409, detail="Диагностика по этой записи уже есть")
    diagnostic = Diagnostic(
        appointment_id=appointment.id,
        master_user_id=user.id,
        findings=data.findings,
        recommended_work=data.recommended_work,
    )
    db.add(diagnostic)
    db.commit()
    db.refresh(diagnostic)
    return diagnostic


@router.get("", response_model=List[DiagnosticOut])
def list_diagnostics(user: User = Depends(require_roles("client", "master", "admin")),
                     db: Session = Depends(get_db)):
    query = select(Diagnostic)
    code = role_code(user, db)
    if code == "master":
        query = query.where(Diagnostic.master_user_id == user.id)
    elif code == "client":
        query = query.join(Appointment, Appointment.id == Diagnostic.appointment_id).where(
            Appointment.client_user_id == user.id)
    return db.scalars(query.order_by(Diagnostic.id.desc()).limit(500)).all()


@router.get("/appointment/{appointment_id}", response_model=DiagnosticOut)
def get_by_appointment(appointment_id: int,
                       user: User = Depends(require_roles("client", "master", "admin")),
                       db: Session = Depends(get_db)):
    appointment = get_visible(db, appointment_id, user)
    diagnostic = db.scalar(select(Diagnostic).where(Diagnostic.appointment_id == appointment.id))
    if diagnostic is None:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    return diagnostic


@router.get("/{diagnostic_id}", response_model=DiagnosticOut)
def get_diagnostic(diagnostic_id: int,
                   user: User = Depends(require_roles("client", "master", "admin")),
                   db: Session = Depends(get_db)):
    diagnostic = db.get(Diagnostic, diagnostic_id)
    if diagnostic is None:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    get_visible(db, diagnostic.appointment_id, user) 
    return diagnostic


@router.patch("/{diagnostic_id}", response_model=DiagnosticOut)
def update_diagnostic(diagnostic_id: int, data: DiagnosticUpdate,
                      user: User = Depends(require_roles("master")),
                      db: Session = Depends(get_db)):
    diagnostic = db.get(Diagnostic, diagnostic_id)
    if diagnostic is None or diagnostic.master_user_id != user.id:
        raise HTTPException(status_code=404, detail="Диагностика не найдена")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field == "findings":
            continue  
        setattr(diagnostic, field, value)
    db.commit()
    db.refresh(diagnostic)
    return diagnostic