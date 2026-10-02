from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class VehicleBase(BaseModel):
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2100)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    license_plate: str = Field(..., min_length=1, max_length=20)
    color: Optional[str] = Field(None, max_length=50)
    mileage: Optional[int] = Field(None, ge=0)
    engine_type: Optional[str] = Field(None, max_length=100)
    transmission: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    make: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1900, le=2100)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    license_plate: Optional[str] = Field(None, min_length=1, max_length=20)
    color: Optional[str] = Field(None, max_length=50)
    mileage: Optional[int] = Field(None, ge=0)
    engine_type: Optional[str] = Field(None, max_length=100)
    transmission: Optional[str] = Field(None, max_length=50)
    fuel_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class VehicleResponse(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class VehicleWithOrders(VehicleResponse):
    orders_count: int = 0
    appointments_count: int = 0