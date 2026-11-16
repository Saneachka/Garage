from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from auth import require_roles
from database import get_db
from models import Appointment, Role, User, Vehicle

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

VIN_ALLOWED = set("ABCDEFGHJKLMNPRSTUVWXYZ0123456789")


def check_vin(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip().upper()
    if len(value) != 17 or not set(value) <= VIN_ALLOWED:
        raise ValueError("VIN: 17 символов, латиница и цифры, без букв I, O, Q")
    return value


class VehicleIn(BaseModel):
    vin: Optional[str] = None
    plate_number: Optional[str] = Field(default=None, max_length=20)
    brand: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    production_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    client_user_id: Optional[int] = None  # только для админа: чья это машина

    _vin = field_validator("vin")(check_vin)


class VehicleUpdate(BaseModel):
    vin: Optional[str] = None
    plate_number: Optional[str] = Field(default=None, max_length=20)
    brand: Optional[str] = Field(default=None, min_length=1, max_length=200)
    model: Optional[str] = Field(default=None, min_length=1, max_length=200)
    production_year: Optional[int] = Field(default=None, ge=1900, le=2100)

    _vin = field_validator("vin")(check_vin)


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_user_id: int
    vin: Optional[str]
    plate_number: Optional[str]
    brand: str
    model: str
    production_year: Optional[int]
    archived_at: Optional[datetime] = None


def is_admin(user: User, db: Session) -> bool:
    return db.get(Role, user.role_id).code == "admin"


def get_accessible(db: Session, vehicle_id: int, user: User) -> Vehicle:
    """Своя машина (или любая, если админ). Чужую не раскрываем: отвечаем 404."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or (vehicle.client_user_id != user.id and not is_admin(user, db)):
        raise HTTPException(status_code=404, detail="Автомобиль не найден")
    return vehicle


def ensure_vin_free(db: Session, vin: Optional[str], exclude_id: Optional[int] = None):
    if vin is None:
        return
    found = db.scalar(select(Vehicle).where(Vehicle.vin == vin))
    if found is not None and found.id != exclude_id:
        raise HTTPException(status_code=409, detail="Автомобиль с таким VIN уже есть")


@router.get("", response_model=List[VehicleOut])
def list_vehicles(include_archived: bool = False,
                  user: User = Depends(require_roles("client", "admin")),
                  db: Session = Depends(get_db)):
    query = select(Vehicle).order_by(Vehicle.id)
    if not is_admin(user, db):
        query = query.where(Vehicle.client_user_id == user.id)
    if not include_archived:
        query = query.where(Vehicle.archived_at.is_(None))
    return db.scalars(query).all()


@router.post("", response_model=VehicleOut, status_code=201)
def create_vehicle(data: VehicleIn, user: User = Depends(require_roles("client", "admin")),
                   db: Session = Depends(get_db)):
    owner_id = user.id
    if is_admin(user, db):
        client = db.get(User, data.client_user_id) if data.client_user_id else None
        if client is None or client.deleted_at is not None \
                or db.get(Role, client.role_id).code != "client":
            raise HTTPException(status_code=422,
                                detail="Укажите client_user_id существующего клиента")
        owner_id = client.id
    ensure_vin_free(db, data.vin)
    vehicle = Vehicle(client_user_id=owner_id, **data.model_dump(exclude={"client_user_id"}))
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, user: User = Depends(require_roles("client", "admin")),
                db: Session = Depends(get_db)):
    return get_accessible(db, vehicle_id, user)


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(vehicle_id: int, data: VehicleUpdate,
                   user: User = Depends(require_roles("client", "admin")),
                   db: Session = Depends(get_db)):
    """Без смены VIN: правим ту же машину. Со сменой VIN (если есть история): новая машина,
    старая уходит в архив и остаётся в истории с прежними данными."""
    vehicle = get_accessible(db, vehicle_id, user)
    if vehicle.archived_at is not None:
        raise HTTPException(status_code=409, detail="Автомобиль в архиве, изменить его нельзя")

    changes = data.model_dump(exclude_unset=True)
    for field in ("brand", "model"):
        if field in changes and changes[field] is None:
            del changes[field]  # обязательные поля нельзя обнулить

    new_vin = changes.get("vin")
    if "vin" in changes:
        if new_vin is None and vehicle.vin is not None:
            raise HTTPException(status_code=422,
                                detail="VIN нельзя удалить, его можно только заменить")
        ensure_vin_free(db, new_vin, exclude_id=vehicle.id)

    vin_replaced = vehicle.vin is not None and new_vin is not None and new_vin != vehicle.vin
    has_history = db.scalar(
        select(Appointment.id).where(Appointment.vehicle_id == vehicle.id).limit(1)
    ) is not None

    if vin_replaced and has_history:
        fields = ("vin", "plate_number", "brand", "model", "production_year")
        new_car = Vehicle(
            client_user_id=vehicle.client_user_id,
            **{f: changes.get(f, getattr(vehicle, f)) for f in fields},
        )
        vehicle.archived_at = datetime.utcnow()
        # У старой машины VIN уникален, поэтому сначала освобождаем его в архиве
        db.add(new_car)
        db.flush()
        # Предстоящие записи переезжают на новую машину, прошлые остаются на старой
        db.execute(
            update(Appointment)
            .where(Appointment.vehicle_id == vehicle.id,
                   Appointment.status.in_(("new", "confirmed")),
                   Appointment.ends_at >= datetime.now())
            .values(vehicle_id=new_car.id)
        )
        db.commit()
        db.refresh(new_car)
        return new_car

    for field, value in changes.items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int, user: User = Depends(require_roles("client", "admin")),
                   db: Session = Depends(get_db)):
    vehicle = get_accessible(db, vehicle_id, user)
    if db.scalar(select(Appointment.id).where(Appointment.vehicle_id == vehicle.id).limit(1)):
        raise HTTPException(status_code=409,
                            detail="Нельзя удалить: у автомобиля есть записи на обслуживание")
    db.delete(vehicle)
    db.commit()