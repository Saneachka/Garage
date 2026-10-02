from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ServiceTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    base_price: float = Field(..., ge=0)
    estimated_duration_minutes: int = Field(..., ge=1)
    is_active: bool = True


class ServiceTypeCreate(ServiceTypeBase):
    pass


class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    base_price: Optional[float] = Field(None, ge=0)
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class ServiceTypeResponse(ServiceTypeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ServiceTypeWithParts(ServiceTypeResponse):
    parts_count: int = 0