from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from auth import require_roles
from database import get_db
from models import (
    Appointment, AppointmentService, AppointmentSlot, Role, ScheduleSlot,
    Service, User, Vehicle,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])

ACTIVE = ("new", "confirmed")  

def check_unique(value):
    if len(set(value)) != len(value):
        raise ValueError("Услуги в списке не должны повторяться")
    return value


def check_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        raise ValueError("Укажите время без часового пояса, например 2026-11-10T09:00:00")
    return value


class AppointmentIn(BaseModel):
    vehicle_id: int
    slot_id: int
    service_ids: List[int] = Field(min_length=1, max_length=20)
    comment: Optional[str] = Field(default=None, max_length=2000)

    _unique = field_validator("service_ids")(check_unique)


class AdminAppointmentIn(BaseModel):
    client_user_id: int
    vehicle_id: int
    master_user_id: int
    starts_at: datetime
    ends_at: datetime
    service_ids: List[int] = Field(default_factory=list, max_length=20)
    comment: Optional[str] = Field(default=None, max_length=2000)

    _unique = field_validator("service_ids")(check_unique)
    _starts = field_validator("starts_at")(check_naive)
    _ends = field_validator("ends_at")(check_naive)

    @model_validator(mode="after")
    def check_order(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Конец периода должен быть позже начала")
        return self


class RescheduleIn(BaseModel):
    new_slot_id: int


class ServiceLine(BaseModel):
    service_id: int
    name: str
    quoted_price: Decimal


class AppointmentOut(BaseModel):
    id: int
    client_user_id: int
    vehicle_id: int
    master_user_id: int
    slot_id: int
    slot_ids: List[int]
    starts_at: datetime
    ends_at: datetime
    status: str
    comment: Optional[str]
    created_at: datetime
    services: List[ServiceLine]
    total_price: Decimal

def role_code(user: User, db: Session) -> str:
    return db.get(Role, user.role_id).code


def slot_minutes(slot: ScheduleSlot) -> float:
    return (slot.ends_at - slot.starts_at).total_seconds() / 60


def to_out(db: Session, a: Appointment) -> AppointmentOut:
    first = db.get(ScheduleSlot, a.slot_id)
    slot_ids = db.scalars(
        select(AppointmentSlot.slot_id)
        .where(AppointmentSlot.appointment_id == a.id)
        .order_by(AppointmentSlot.slot_id)
    ).all()
    rows = db.execute(
        select(AppointmentService, Service)
        .join(Service, Service.id == AppointmentService.service_id)
        .where(AppointmentService.appointment_id == a.id)
        .order_by(Service.name)
    ).all()
    lines = [
        ServiceLine(service_id=s.id, name=s.name, quoted_price=link.quoted_price)
        for link, s in rows
    ]
    return AppointmentOut(
        id=a.id,
        client_user_id=a.client_user_id,
        vehicle_id=a.vehicle_id,
        master_user_id=first.master_user_id,
        slot_id=a.slot_id,
        slot_ids=list(slot_ids),
        starts_at=a.starts_at,
        ends_at=a.ends_at,
        status=a.status,
        comment=a.comment,
        created_at=a.created_at,
        services=lines,
        total_price=sum((l.quoted_price for l in lines), Decimal("0")),
    )


def get_visible(db: Session, appointment_id: int, user: User) -> Appointment:
    a = db.get(Appointment, appointment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    code = role_code(user, db)
    if code == "client" and a.client_user_id != user.id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if code == "master" and db.get(ScheduleSlot, a.slot_id).master_user_id != user.id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return a


def get_active_master(db: Session, master_id: int) -> User:
    user = db.get(User, master_id)
    if user is None or user.deleted_at is not None or role_code(user, db) != "master":
        raise HTTPException(status_code=404, detail="Мастер не найден")
    return user


def get_active_services(db: Session, service_ids: List[int]) -> List[Service]:
    if not service_ids:
        return []
    services = db.scalars(select(Service).where(Service.id.in_(service_ids))).all()
    if len(services) != len(service_ids) or any(not s.is_active for s in services):
        raise HTTPException(status_code=422, detail="Одна из услуг не найдена или отключена")
    return services


def collect_block(db: Session, start_slot_id: int, total_minutes: float) -> List[ScheduleSlot]:
    first = db.get(ScheduleSlot, start_slot_id)
    if first is None:
        raise HTTPException(status_code=404, detail="Слот не найден")
    get_active_master(db, first.master_user_id)
    if first.starts_at <= datetime.now():
        raise HTTPException(status_code=409, detail="Слот уже в прошлом")

    candidates = db.scalars(
        select(ScheduleSlot)
        .where(ScheduleSlot.master_user_id == first.master_user_id,
               ScheduleSlot.starts_at >= first.starts_at)
        .order_by(ScheduleSlot.starts_at)
        .limit(48)
    ).all()

    block, covered, prev_end = [], 0.0, None
    for s in candidates:
        if prev_end is not None and s.starts_at != prev_end:
            break  
        if not s.is_available:
            break
        block.append(s)
        covered += slot_minutes(s)
        prev_end = s.ends_at
        if covered >= total_minutes:
            return block

    if not block:
        raise HTTPException(status_code=409, detail="Слот уже занят")
    raise HTTPException(
        status_code=409,
        detail="Подряд свободно только %d мин, а нужно %d мин. Выберите другое время"
               % (covered, total_minutes),
    )

def free_block(db: Session, master_id: int, starts_at: datetime,
               total_minutes: float) -> Optional[List[ScheduleSlot]]:
    """Подряд идущие свободные слоты мастера от точного времени starts_at, либо None."""
    candidates = db.scalars(
        select(ScheduleSlot)
        .where(ScheduleSlot.master_user_id == master_id, ScheduleSlot.starts_at >= starts_at)
        .order_by(ScheduleSlot.starts_at)
        .limit(48)
    ).all()
    if not candidates or candidates[0].starts_at != starts_at:
        return None
    block, covered, prev_end = [], 0.0, None
    for s in candidates:
        if (prev_end is not None and s.starts_at != prev_end) or not s.is_available:
            return None
        block.append(s)
        covered += slot_minutes(s)
        prev_end = s.ends_at
        if covered >= total_minutes:
            return block
    return None



def claim_slots(db: Session, slot_ids: List[int]):
    result = db.execute(
        update(ScheduleSlot)
        .where(ScheduleSlot.id.in_(slot_ids), ScheduleSlot.is_available.is_(True))
        .values(is_available=False)
    )
    if result.rowcount != len(slot_ids):
        db.rollback()
        raise HTTPException(status_code=409, detail="Слот уже занят")


def reserve(db: Session, appointment: Appointment, slots: List[ScheduleSlot]):
    for s in slots:
        db.add(AppointmentSlot(slot_id=s.id, appointment_id=appointment.id))


def release_slots(db: Session, appointment_id: int):
    ids = db.scalars(
        select(AppointmentSlot.slot_id).where(AppointmentSlot.appointment_id == appointment_id)
    ).all()
    if not ids:
        return
    db.execute(delete(AppointmentSlot).where(AppointmentSlot.appointment_id == appointment_id))
    db.execute(update(ScheduleSlot).where(ScheduleSlot.id.in_(ids)).values(is_available=True))


def add_service_lines(db: Session, appointment: Appointment, services: List[Service]):
    for s in services:
        db.add(AppointmentService(
            appointment_id=appointment.id, service_id=s.id, quoted_price=s.price,
        ))

@router.post("", response_model=AppointmentOut, status_code=201)
def create_appointment(data: AppointmentIn, user: User = Depends(require_roles("client")),
                       db: Session = Depends(get_db)):
    vehicle = db.get(Vehicle, data.vehicle_id)
    if vehicle is None or vehicle.client_user_id != user.id:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    services = get_active_services(db, data.service_ids)
    total = sum(s.duration_minutes for s in services)
    block = collect_block(db, data.slot_id, total)
    claim_slots(db, [s.id for s in block])

    appointment = Appointment(
        client_user_id=user.id,
        vehicle_id=vehicle.id,
        slot_id=block[0].id,
        starts_at=block[0].starts_at,
        ends_at=block[-1].ends_at,
        status="new",
        comment=data.comment,
    )
    db.add(appointment)
    db.flush()
    reserve(db, appointment, block)
    add_service_lines(db, appointment, services)
    db.commit()
    db.refresh(appointment)
    return to_out(db, appointment)


@router.post("/admin", response_model=AppointmentOut, status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_appointment_by_admin(data: AdminAppointmentIn, db: Session = Depends(get_db)):
    """Сложные работы: администратор резервирует все слоты мастера в периоде (хоть на несколько дней)."""
    client = db.get(User, data.client_user_id)
    if client is None or client.deleted_at is not None or role_code(client, db) != "client":
        raise HTTPException(status_code=404, detail="Клиент не найден")
    vehicle = db.get(Vehicle, data.vehicle_id)
    if vehicle is None or vehicle.client_user_id != client.id:
        raise HTTPException(status_code=404, detail="Автомобиль этого клиента не найден")
    get_active_master(db, data.master_user_id)
    services = get_active_services(db, data.service_ids)

    if data.starts_at <= datetime.now():
        raise HTTPException(status_code=422, detail="Начало периода должно быть в будущем")

    slots = db.scalars(
        select(ScheduleSlot)
        .where(ScheduleSlot.master_user_id == data.master_user_id,
               ScheduleSlot.starts_at >= data.starts_at,
               ScheduleSlot.ends_at <= data.ends_at)
        .order_by(ScheduleSlot.starts_at)
    ).all()
    if not slots:
        raise HTTPException(status_code=422, detail="В этом периоде у мастера нет слотов")
    busy = [s.starts_at.strftime("%d.%m %H:%M") for s in slots if not s.is_available]
    if busy:
        raise HTTPException(
            status_code=409,
            detail="Заняты слоты: %s. Ничего не зарезервировано" % ", ".join(busy[:10]),
        )

    claim_slots(db, [s.id for s in slots])
    appointment = Appointment(
        client_user_id=client.id,
        vehicle_id=vehicle.id,
        slot_id=slots[0].id,
        starts_at=slots[0].starts_at,
        ends_at=slots[-1].ends_at,
        status="confirmed",  
        comment=data.comment,
    )
    db.add(appointment)
    db.flush()
    reserve(db, appointment, slots)
    add_service_lines(db, appointment, services)
    db.commit()
    db.refresh(appointment)
    return to_out(db, appointment)


@router.get("", response_model=List[AppointmentOut])
def list_appointments(
    status: Optional[str] = None,
    scope: Optional[str] = None,  # upcoming = предстоящие, history = история
    user: User = Depends(require_roles("client", "master", "admin")),
    db: Session = Depends(get_db),
):
    query = select(Appointment).join(ScheduleSlot, ScheduleSlot.id == Appointment.slot_id)
    code = role_code(user, db)
    if code == "client":
        query = query.where(Appointment.client_user_id == user.id)
    elif code == "master":
        query = query.where(ScheduleSlot.master_user_id == user.id)

    now = datetime.now()
    if status:
        query = query.where(Appointment.status == status)
    if scope == "upcoming":
        query = query.where(Appointment.status.in_(ACTIVE), Appointment.ends_at >= now)
    elif scope == "history":
        query = query.where((Appointment.status.notin_(ACTIVE)) | (Appointment.ends_at < now))
    items = db.scalars(query.order_by(Appointment.starts_at.desc()).limit(500)).all()
    return [to_out(db, a) for a in items]

@router.get("/availability")
def availability(day: date, master_user_id: int, service_ids: List[int] = Query(...),
                 db: Session = Depends(get_db)):
    """С каких слотов мастера можно начать выбранные услуги в этот день. Вход не нужен."""
    get_active_master(db, master_user_id)
    services = get_active_services(db, service_ids)
    total = sum(s.duration_minutes for s in services)
    day_start = datetime.combine(day, time.min)
    slots = db.scalars(
        select(ScheduleSlot)
        .where(ScheduleSlot.master_user_id == master_user_id,
               ScheduleSlot.starts_at >= max(day_start, datetime.now()),
               ScheduleSlot.starts_at < day_start + timedelta(days=1),
               ScheduleSlot.is_available.is_(True))
        .order_by(ScheduleSlot.starts_at)
    ).all()
    result = []
    for s in slots:
        block = free_block(db, master_user_id, s.starts_at, total)
        if block:
            result.append({"slot_id": s.id, "starts_at": s.starts_at, "ends_at": block[-1].ends_at})
    return result

@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int,
                    user: User = Depends(require_roles("client", "master", "admin")),
                    db: Session = Depends(get_db)):
    return to_out(db, get_visible(db, appointment_id, user))


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(appointment_id: int,
                       user: User = Depends(require_roles("client", "admin")),
                       db: Session = Depends(get_db)):
    a = get_visible(db, appointment_id, user)
    if a.status not in ACTIVE:
        raise HTTPException(status_code=409, detail="Эту запись нельзя отменить")
    if role_code(user, db) == "client" and a.starts_at <= datetime.now():
        raise HTTPException(status_code=409, detail="Время записи уже наступило")
    a.status = "cancelled"
    release_slots(db, a.id)
    db.commit()
    db.refresh(a)
    return to_out(db, a)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(appointment_id: int, data: RescheduleIn,
                           user: User = Depends(require_roles("client", "admin")),
                           db: Session = Depends(get_db)):
    a = get_visible(db, appointment_id, user)
    if a.status not in ACTIVE:
        raise HTTPException(status_code=409, detail="Эту запись нельзя перенести")
    if role_code(user, db) == "client" and a.starts_at <= datetime.now():
        raise HTTPException(status_code=409, detail="Время записи уже наступило")

    current = db.scalars(
        select(ScheduleSlot)
        .join(AppointmentSlot, AppointmentSlot.slot_id == ScheduleSlot.id)
        .where(AppointmentSlot.appointment_id == a.id)
        .order_by(ScheduleSlot.starts_at)
    ).all()

    for prev, nxt in zip(current, current[1:]):
        if prev.ends_at != nxt.starts_at:
            raise HTTPException(
                status_code=409,
                detail="Многодневную запись нельзя перенести: отмените её и создайте новую",
            )
    if current and data.new_slot_id == current[0].id:
        raise HTTPException(status_code=422, detail="Выберите другое время")

    total = sum(slot_minutes(s) for s in current)
    release_slots(db, a.id)  
    block = collect_block(db, data.new_slot_id, total)  
    claim_slots(db, [s.id for s in block])
    reserve(db, a, block)
    a.slot_id = block[0].id
    a.starts_at = block[0].starts_at
    a.ends_at = block[-1].ends_at
    if role_code(user, db) == "client":
        a.status = "new"  
    db.commit()
    db.refresh(a)
    return to_out(db, a)


@router.post("/{appointment_id}/confirm", response_model=AppointmentOut,
             dependencies=[Depends(require_roles("admin"))])
def confirm_appointment(appointment_id: int, db: Session = Depends(get_db)):
    a = db.get(Appointment, appointment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    if a.status != "new":
        raise HTTPException(status_code=409, detail="Подтвердить можно только новую запись")
    a.status = "confirmed"
    db.commit()
    db.refresh(a)
    return to_out(db, a)


@router.post("/{appointment_id}/complete", response_model=AppointmentOut)
def complete_appointment(appointment_id: int,
                         user: User = Depends(require_roles("master", "admin")),
                         db: Session = Depends(get_db)):
    a = get_visible(db, appointment_id, user)
    if a.status != "confirmed":
        raise HTTPException(status_code=409, detail="Завершить можно только подтверждённую запись")
    a.status = "completed"
    db.commit()
    db.refresh(a)
    return to_out(db, a)