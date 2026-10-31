from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import require_roles
from database import get_db
from models import Service

router = APIRouter(prefix="/services", tags=["services"])


class ServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    duration_minutes: int = Field(gt=0, le=32000)
    is_active: bool = True


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    duration_minutes: Optional[int] = Field(default=None, gt=0, le=32000)
    is_active: Optional[bool] = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    price: Decimal
    duration_minutes: int
    is_active: bool


def get_or_404(db: Session, service_id: int) -> Service:
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return service


@router.get("", response_model=List[ServiceOut])
def list_services(db: Session = Depends(get_db)):
    """Каталог: только активные услуги, вход не нужен."""
    return db.scalars(
        select(Service).where(Service.is_active.is_(True)).order_by(Service.name)
    ).all()


@router.get("/all", response_model=List[ServiceOut], dependencies=[Depends(require_roles("admin"))])
def list_all_services(db: Session = Depends(get_db)):
    return db.scalars(select(Service).order_by(Service.name)).all()


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = get_or_404(db, service_id)
    if not service.is_active:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return service


@router.post("", response_model=ServiceOut, status_code=201,
             dependencies=[Depends(require_roles("admin"))])
def create_service(data: ServiceIn, db: Session = Depends(get_db)):
    service = Service(**data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.patch("/{service_id}", response_model=ServiceOut,
              dependencies=[Depends(require_roles("admin"))])
def update_service(service_id: int, data: ServiceUpdate, db: Session = Depends(get_db)):
    service = get_or_404(db, service_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None and field != "description":
            continue  # обязательные поля нельзя обнулить
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", response_model=ServiceOut,
               dependencies=[Depends(require_roles("admin"))])
def disable_service(service_id: int, db: Session = Depends(get_db)):
    """Услугу не удаляем, а отключаем: на неё могут ссылаться старые записи."""
    service = get_or_404(db, service_id)
    service.is_active = False
    db.commit()
    db.refresh(service)
    return service