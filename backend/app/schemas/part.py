from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PartBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    part_number: str = Field(..., min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    purchase_price: float = Field(..., ge=0)
    sale_price: float = Field(..., ge=0)
    quantity_in_stock: int = Field(default=0, ge=0)
    min_stock_level: int = Field(default=5, ge=0)
    unit: str = Field(default="pcs", max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class PartCreate(PartBase):
    service_type_id: Optional[int] = None


class PartUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    part_number: Optional[str] = Field(None, min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    purchase_price: Optional[float] = Field(None, ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    quantity_in_stock: Optional[int] = Field(None, ge=0)
    min_stock_level: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    service_type_id: Optional[int] = None


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_type_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_in_stock <= self.min_stock_level


class PartWithServiceType(PartResponse):
    service_type: Optional["ServiceTypeResponse"] = None


class StockMovementBase(BaseModel):
    part_id: int
    movement_type: str = Field(..., pattern="^(in|out|adjustment|return|transfer)$")
    quantity: int = Field(..., gt=0)
    reference_type: Optional[str] = Field(None, max_length=50)
    reference_id: Optional[int] = None
    notes: Optional[str] = None


class StockMovementCreate(StockMovementBase):
    pass


class StockMovementResponse(StockMovementBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class PartWithMovements(PartResponse):
    stock_movements: list[StockMovementResponse] = []