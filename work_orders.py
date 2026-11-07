from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from appointments import get_active_master, role_code
from auth import require_roles
from database import get_db
from models import Appointment, AppointmentService, User, WorkOrder, WorkOrderPart

router = APIRouter(prefix="/work-orders", tags=["work-orders"])

TRANSITIONS = {
    "new": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
}
MASTER_ALLOWED = {"in_progress", "completed"}  # отменять наряд может только администратор
CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


# ---------- схемы ----------
class PartIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class PartUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    quantity: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    unit_price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class PartOut(BaseModel):
    id: int
    name: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal


class WorkOrderIn(BaseModel):
    appointment_id: int
    master_user_id: int
    work_description: str = Field(min_length=1, max_length=10000)
    # Простые операции: не указывать, возьмётся сумма услуг записи. Сложные: админ задаёт сам.
    work_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    parts: List[PartIn] = Field(default_factory=list, max_length=100)


class WorkOrderUpdate(BaseModel):
    master_user_id: Optional[int] = None
    work_description: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    work_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class StatusIn(BaseModel):
    status: str


class WorkOrderOut(BaseModel):
    id: int
    appointment_id: int
    master_user_id: int
    created_by: int
    work_description: str
    work_cost: Decimal
    parts_cost: Decimal
    total_cost: Decimal
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    parts: List[PartOut]


# ---------- вспомогательное ----------
def load_parts(db: Session, order_id: int) -> List[WorkOrderPart]:
    return db.scalars(
        select(WorkOrderPart).where(WorkOrderPart.work_order_id == order_id)
        .order_by(WorkOrderPart.id)
    ).all()


def recalc(db: Session, order: WorkOrder):
    """Итог = работы + запчасти."""
    parts_cost = sum((money(p.quantity * p.unit_price) for p in load_parts(db, order.id)),
                     Decimal("0"))
    order.total_cost = money(order.work_cost + parts_cost)


def to_out(db: Session, order: WorkOrder) -> WorkOrderOut:
    lines = [
        PartOut(id=p.id, name=p.name, quantity=p.quantity, unit_price=p.unit_price,
                total=money(p.quantity * p.unit_price))
        for p in load_parts(db, order.id)
    ]
    return WorkOrderOut(
        id=order.id,
        appointment_id=order.appointment_id,
        master_user_id=order.master_user_id,
        created_by=order.created_by,
        work_description=order.work_description,
        work_cost=order.work_cost,
        parts_cost=sum((l.total for l in lines), Decimal("0")),
        total_cost=order.total_cost,
        status=order.status,
        created_at=order.created_at,
        completed_at=order.completed_at,
        parts=lines,
    )


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


def get_editable(db: Session, order_id: int) -> WorkOrder:
    order = db.get(WorkOrder, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Заказ-наряд не найден")
    if order.status not in TRANSITIONS:
        raise HTTPException(status_code=409,
                            detail="Завершённый или отменённый наряд менять нельзя")
    return order


# ---------- наряды ----------
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

    work_cost = data.work_cost
    if work_cost is None:  # простая операция: цена услуг на момент записи
        prices = db.scalars(
            select(AppointmentService.quoted_price)
            .where(AppointmentService.appointment_id == appointment.id)
        ).all()
        work_cost = sum(prices, Decimal("0"))

    order = WorkOrder(
        appointment_id=appointment.id,
        master_user_id=data.master_user_id,
        created_by=user.id,
        work_description=data.work_description,
        work_cost=money(work_cost),
        total_cost=money(work_cost),
        status="new",
    )
    db.add(order)
    db.flush()
    for part in data.parts:
        db.add(WorkOrderPart(work_order_id=order.id, **part.model_dump()))
    db.flush()
    recalc(db, order)
    db.commit()
    db.refresh(order)
    return to_out(db, order)


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
    orders = db.scalars(query.order_by(WorkOrder.id.desc()).limit(500)).all()
    return [to_out(db, o) for o in orders]


@router.get("/{order_id}", response_model=WorkOrderOut)
def get_work_order(order_id: int,
                   user: User = Depends(require_roles("client", "master", "admin")),
                   db: Session = Depends(get_db)):
    return to_out(db, get_visible(db, order_id, user))


@router.patch("/{order_id}", response_model=WorkOrderOut,
              dependencies=[Depends(require_roles("admin"))])
def update_work_order(order_id: int, data: WorkOrderUpdate, db: Session = Depends(get_db)):
    order = get_editable(db, order_id)
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "master_user_id" in changes:
        get_active_master(db, changes["master_user_id"])
    for field, value in changes.items():
        setattr(order, field, money(value) if field == "work_cost" else value)
    recalc(db, order)
    db.commit()
    db.refresh(order)
    return to_out(db, order)


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
    return to_out(db, order)


# ---------- запчасти (только администратор) ----------
@router.post("/{order_id}/parts", response_model=WorkOrderOut, status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def add_part(order_id: int, data: PartIn, db: Session = Depends(get_db)):
    order = get_editable(db, order_id)
    db.add(WorkOrderPart(work_order_id=order.id, **data.model_dump()))
    db.flush()
    recalc(db, order)
    db.commit()
    db.refresh(order)
    return to_out(db, order)


@router.patch("/{order_id}/parts/{part_id}", response_model=WorkOrderOut,
              dependencies=[Depends(require_roles("admin"))])
def update_part(order_id: int, part_id: int, data: PartUpdate, db: Session = Depends(get_db)):
    order = get_editable(db, order_id)
    part = db.get(WorkOrderPart, part_id)
    if part is None or part.work_order_id != order.id:
        raise HTTPException(status_code=404, detail="Запчасть не найдена")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(part, field, value)
    db.flush()
    recalc(db, order)
    db.commit()
    db.refresh(order)
    return to_out(db, order)


@router.delete("/{order_id}/parts/{part_id}", response_model=WorkOrderOut,
               dependencies=[Depends(require_roles("admin"))])
def delete_part(order_id: int, part_id: int, db: Session = Depends(get_db)):
    order = get_editable(db, order_id)
    part = db.get(WorkOrderPart, part_id)
    if part is None or part.work_order_id != order.id:
        raise HTTPException(status_code=404, detail="Запчасть не найдена")
    db.delete(part)
    db.flush()
    recalc(db, order)
    db.commit()
    db.refresh(order)
    return to_out(db, order)