from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from appointments import get_active_master, role_code
from auth import require_roles
from database import get_db
from models import Appointment, AppointmentService, WorkOrder, User

router = APIRouter(prefix="/work-orders", tags=["work-orders"])

TRANSITIONS = {
    "new": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
}
MASTER_ALLOWED = {"in_progress", "completed"}  # отменять наряд может только администратор


class WorkOrderIn(BaseModel):
    appointment_id: int
    master_user_id: int
    work_description: str = Field(min_length=1, max_length=10000)
    total_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class WorkOrderUpdate(BaseModel):
    master_user_id: Optional[int] = None
    work_description: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    total_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class StatusIn(BaseModel):
    status: str


class WorkOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    master_user_id: int
    created_by: int
    work_description: str
    total_cost: Decimal
    status: str
    created_at: datetime
    completed_at: Optional[datetime]


def get_visible(db: Session, order_id: int, user: User) -> WorkOrder:
    order = db.get(WorkOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ-наряд не найден")
    code = role_code(user, db)
    if code == "master" and order.master_user_id != user.id:
        raise HTTPException(status_code=404, detail="Заказ-наряд не найден")
    if code == "client":
        appointment = db.get(Appointment, order.appointment_id)
        if appointment.client_user_id != user.id:
            raise HTTPException(status_code=404, detail="Заказ-наряд не найден")
    return order


@router.post("", response_model=WorkOrderOut, status_code=201)
def create_work_order(data: WorkOrderIn, user: User = Depends(require_roles("admin")),
                      db: Session = Depends(get_db)):
    appointment = db.get(Appointment, data.appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if appointment.status == "cancelled":
        raise HTTPException(status_code=409, detail="Запись отменена")
    if db.scalar(select(WorkOrder.id).where(WorkOrder.appointment_id == appointment.id)):
        raise HTTPException(status_code=409, detail="Заказ-наряд по этой записи уже есть")
    get_active_master(db, data.master_user_id)

    cost = data.total_cost
    if cost is None:  # по умолчанию: сумма цен услуг записи
        prices = db.scalars(
            select(AppointmentService.quoted_price)
            .where(AppointmentService.appointment_id == appointment.id)
        ).all()
        cost = sum(prices, Decimal("0"))

    order = WorkOrder(
        appointment_id=appointment.id,
        master_user_id=data.master_user_id,
        created_by=user.id,
        work_description=data.work_description,
        total_cost=cost,
        status="new",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=List[WorkOrderOut])
def list_work_orders(status: Optional[str] = None,
                     user: User = Depends(require_roles("client", "master", "admin")),
                     db: Session = Depends(get_db)):
    query = select(WorkOrder)
    code = role_code(user, db)
    if code == "master":
        query = query.where(WorkOrder.master_user_id == user.id)
    elif code == "client":
        query = query.join(Appointment, Appointment.id == WorkOrder.appointment_id).where(
            Appointment.client_user_id == user.id)
    if status:
        query = query.where(WorkOrder.status == status)
    return db.scalars(query.order_by(WorkOrder.id.desc()).limit(500)).all()


@router.get("/{order_id}", response_model=WorkOrderOut)
def get_work_order(order_id: int,
                   user: User = Depends(require_roles("client", "master", "admin")),
                   db: Session = Depends(get_db)):
    return get_visible(db, order_id, user)


@router.patch("/{order_id}", response_model=WorkOrderOut,
              dependencies=[Depends(require_roles("admin"))])
def update_work_order(order_id: int, data: WorkOrderUpdate, db: Session = Depends(get_db)):
    order = db.get(WorkOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ-наряд не найден")
    if order.status not in TRANSITIONS:
        raise HTTPException(status_code=409, detail="Завершённый или отменённый наряд менять нельзя")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("master_user_id") is not None:
        get_active_master(db, changes["master_user_id"])
    for field, value in changes.items():
        if value is None:
            continue  # все поля обязательные, обнулять нельзя
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/status", response_model=WorkOrderOut)
def change_status(order_id: int, data: StatusIn,
                  user: User = Depends(require_roles("master", "admin")),
                  db: Session = Depends(get_db)):
    order = get_visible(db, order_id, user)
    allowed = TRANSITIONS.get(order.status, set())
    if data.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail="Из статуса «%s» можно перейти только в: %s"
                   % (order.status, ", ".join(sorted(allowed)) or "переходы невозможны"),
        )
    if role_code(user, db) == "master" and data.status not in MASTER_ALLOWED:
        raise HTTPException(status_code=403, detail="Отменить наряд может только администратор")
    order.status = data.status
    if data.status == "completed":
        order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order