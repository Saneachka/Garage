from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.models import Appointment, AppointmentService, WorkOrder, WorkOrderPart

CENT = Decimal("0.01")

# Статус записи -> статус наряда. У записи «new» наряда ещё нет.
ORDER_STATUS = {
    "confirmed": "new",
    "in_progress": "in_progress",
    "completed": "completed",
    "cancelled": "cancelled",
}


class PartIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def load_parts(db: Session, order_id: int) -> List[WorkOrderPart]:
    return db.scalars(
        select(WorkOrderPart).where(WorkOrderPart.work_order_id == order_id)
        .order_by(WorkOrderPart.id)
    ).all()


def recalc(db: Session, order: WorkOrder):
    """Итого = работы + запчасти."""
    parts_cost = sum((money(p.quantity * p.unit_price) for p in load_parts(db, order.id)),
                     Decimal("0"))
    order.total_cost = money(order.work_cost + parts_cost)


def get_order(db: Session, appointment_id: int) -> Optional[WorkOrder]:
    return db.scalar(select(WorkOrder).where(WorkOrder.appointment_id == appointment_id))


def services_cost(db: Session, appointment_id: int) -> Decimal:
    prices = db.scalars(
        select(AppointmentService.quoted_price)
        .where(AppointmentService.appointment_id == appointment_id)
    ).all()
    return sum(prices, Decimal("0"))


def create_order(db: Session, appointment: Appointment, master_id: int, created_by: int,
                 description: str, work_cost=None, parts=()) -> WorkOrder:
    """Создаёт наряд для записи. Статус наряда берётся из статуса записи."""
    if appointment.status not in ORDER_STATUS:
        raise HTTPException(status_code=409,
                            detail="Заказ-наряд создаётся после подтверждения записи")
    if get_order(db, appointment.id) is not None:
        raise HTTPException(status_code=409, detail="Заказ-наряд по этой записи уже есть")
    if work_cost is None:  # из каталога: цена услуг на момент записи
        work_cost = services_cost(db, appointment.id)
    order = WorkOrder(
        appointment_id=appointment.id,
        master_user_id=master_id,
        created_by=created_by,
        work_description=description,
        work_cost=money(work_cost),
        total_cost=money(work_cost),
        status=ORDER_STATUS[appointment.status],
        completed_at=datetime.utcnow() if appointment.status == "completed" else None,
    )
    db.add(order)
    db.flush()
    for part in parts:
        db.add(WorkOrderPart(work_order_id=order.id, **part.model_dump()))
    db.flush()
    recalc(db, order)
    return order