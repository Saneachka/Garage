from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import hash_password, require_roles
from database import get_db
from models import Appointment, Role, ScheduleSlot, User, AppointmentSlot, UserGroupMember

masters_router = APIRouter(prefix="/masters", tags=["masters"])
slots_router = APIRouter(prefix="/slots", tags=["slots"])


class MasterIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=30)


class MasterAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: Optional[str]


class MasterPublic(BaseModel):
    """Для клиентов: только то, что нужно для выбора специалиста."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


def get_master_or_404(db: Session, master_id: int) -> User:
    user = db.get(User, master_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    if db.get(Role, user.role_id).code != "master":
        raise HTTPException(status_code=404, detail="Мастер не найден")
    return user


@masters_router.get("", response_model=List[MasterPublic])
def list_masters(group_id: Optional[int] = None, db: Session = Depends(get_db)):
    role = db.scalar(select(Role).where(Role.code == "master"))
    if role is None:
        return []
    query = select(User).where(User.role_id == role.id, User.deleted_at.is_(None))
    if group_id is not None:
        query = query.where(User.id.in_(
            select(UserGroupMember.user_id).where(UserGroupMember.group_id == group_id)))
    return db.scalars(query.order_by(User.full_name)).all()


@masters_router.post("", response_model=MasterAdminOut, status_code=201,
                     dependencies=[Depends(require_roles("admin"))])
def create_master(data: MasterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Почта уже зарегистрирована")
    role = db.scalar(select(Role).where(Role.code == "master"))
    user = User(
        role_id=role.id,
        full_name=data.full_name,
        email=email,
        password_hash=hash_password(data.password),
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@masters_router.delete("/{master_id}", status_code=204,
                       dependencies=[Depends(require_roles("admin"))])
def delete_master(master_id: int, db: Session = Depends(get_db)):
    """Мягкое удаление: история записей остаётся, войти и получить слоты он больше не сможет."""
    master = get_master_or_404(db, master_id)
    master.deleted_at = datetime.utcnow()
    db.commit()


def naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        raise ValueError("Укажите время без часового пояса, например 2026-11-10T09:00:00")
    return value


class SlotIn(BaseModel):
    master_user_id: int
    starts_at: datetime
    ends_at: datetime

    _starts = field_validator("starts_at")(naive)
    _ends = field_validator("ends_at")(naive)

    @model_validator(mode="after")
    def check_order(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Конец слота должен быть позже начала")
        return self


class SlotBulkIn(BaseModel):
    master_user_id: int
    day: date
    start_time: time
    end_time: time
    slot_minutes: int = Field(ge=15, le=480)

    @model_validator(mode="after")
    def check_order(self):
        if self.end_time <= self.start_time:
            raise ValueError("Конец рабочего времени должен быть позже начала")
        return self


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    master_user_id: int
    starts_at: datetime
    ends_at: datetime
    is_available: bool


def has_overlap(db: Session, master_id: int, starts: datetime, ends: datetime) -> bool:
    found = db.scalar(
        select(ScheduleSlot.id)
        .where(
            ScheduleSlot.master_user_id == master_id,
            ScheduleSlot.starts_at < ends,
            ScheduleSlot.ends_at > starts,
        )
        .limit(1)
    )
    return found is not None


def apply_filters(query, master_user_id, date_from, date_to):
    if master_user_id is not None:
        query = query.where(ScheduleSlot.master_user_id == master_user_id)
    if date_from is not None:
        query = query.where(ScheduleSlot.starts_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        query = query.where(
            ScheduleSlot.starts_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    return query


@slots_router.get("", response_model=List[SlotOut])
def list_free_slots(
    master_user_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Свободные будущие слоты. Вход не нужен."""
    query = (
        select(ScheduleSlot)
        .join(User, User.id == ScheduleSlot.master_user_id)
        .where(
            User.deleted_at.is_(None),
            ScheduleSlot.is_available.is_(True),
            ScheduleSlot.starts_at >= datetime.now(),
        )
    )
    query = apply_filters(query, master_user_id, date_from, date_to)
    return db.scalars(query.order_by(ScheduleSlot.starts_at).limit(500)).all()


@slots_router.get("/all", response_model=List[SlotOut])
def list_all_slots(
    master_user_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user: User = Depends(require_roles("admin", "master")),
    db: Session = Depends(get_db),
):
## Все слоты, в том числе занятые. Мастер видит только свои, админ любые
    if db.get(Role, user.role_id).code == "master":
        master_user_id = user.id
    query = apply_filters(select(ScheduleSlot), master_user_id, date_from, date_to)
    return db.scalars(query.order_by(ScheduleSlot.starts_at).limit(500)).all()


@slots_router.post("", response_model=SlotOut, status_code=201,
                   dependencies=[Depends(require_roles("admin"))])
def create_slot(data: SlotIn, db: Session = Depends(get_db)):
    get_master_or_404(db, data.master_user_id)
    if has_overlap(db, data.master_user_id, data.starts_at, data.ends_at):
        raise HTTPException(status_code=409, detail="Слот пересекается с существующим")
    slot = ScheduleSlot(
        master_user_id=data.master_user_id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@slots_router.post("/bulk", response_model=List[SlotOut], status_code=201,
                   dependencies=[Depends(require_roles("admin"))])
def create_slots_bulk(data: SlotBulkIn, db: Session = Depends(get_db)):
    """Нарезает рабочий день на слоты одинаковой длины."""
    get_master_or_404(db, data.master_user_id)
    step = timedelta(minutes=data.slot_minutes)
    current = datetime.combine(data.day, data.start_time)
    day_end = datetime.combine(data.day, data.end_time)

    new_slots = []
    while current + step <= day_end:
        if has_overlap(db, data.master_user_id, current, current + step):
            raise HTTPException(
                status_code=409,
                detail="Слот %s пересекается с существующим, ничего не создано"
                       % current.strftime("%H:%M"),
            )
        new_slots.append(ScheduleSlot(
            master_user_id=data.master_user_id,
            starts_at=current,
            ends_at=current + step,
        ))
        current += step

    if not new_slots:
        raise HTTPException(status_code=422,
                            detail="В указанный интервал не помещается ни один слот")
    db.add_all(new_slots)
    db.commit()
    for slot in new_slots:
        db.refresh(slot)
    return new_slots

@slots_router.delete("/{slot_id}", status_code=204,
                     dependencies=[Depends(require_roles("admin"))])
def delete_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.get(ScheduleSlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Слот не найден")
    busy = db.scalar(select(Appointment.id).where(Appointment.slot_id == slot.id).limit(1)) \
        or db.scalar(select(AppointmentSlot.slot_id).where(AppointmentSlot.slot_id == slot.id).limit(1))
    if busy:
        raise HTTPException(status_code=409, detail="Нельзя удалить: на слот есть запись")
    db.delete(slot)
    db.commit()

    