from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
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
def list_vehicles(user: User = Depends(require_roles("client", "admin")),
                  db: Session = Depends(get_db)):
    query = select(Vehicle).order_by(Vehicle.id)
    if not is_admin(user, db):
        query = query.where(Vehicle.client_user_id == user.id)
    return db.scalars(query).all()


@router.post("", response_model=VehicleOut, status_code=201)
def create_vehicle(data: VehicleIn, user: User = Depends(require_roles("client")),
                   db: Session = Depends(get_db)):
    ensure_vin_free(db, data.vin)
    vehicle = Vehicle(client_user_id=user.id, **data.model_dump())
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
                   user: User = Depends(require_roles("client")),
                   db: Session = Depends(get_db)):
    vehicle = get_accessible(db, vehicle_id, user)
    changes = data.model_dump(exclude_unset=True)
    if "vin" in changes:
        ensure_vin_free(db, changes["vin"], exclude_id=vehicle.id)
    for field, value in changes.items():
        if value is None and field in ("brand", "model"):
            continue  # обязательные поля нельзя обнулить
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