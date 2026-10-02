from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.service_type import ServiceTypeResponse
from app.schemas.part import PartResponse


class OrderItemBase(BaseModel):
    service_type_id: Optional[int] = None
    part_id: Optional[int] = None
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)
    description: Optional[str] = None
    is_labor: bool = False


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=1)
    unit_price: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None


class OrderItemResponse(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    total_price: float
    created_at: datetime
    service_type: Optional[ServiceTypeResponse] = None
    part: Optional[PartResponse] = None


class OrderBase(BaseModel):
    vehicle_id: int
    description: Optional[str] = None
    customer_notes: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    vehicle_id: Optional[int] = None
    mechanic_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(draft|pending|confirmed|in_progress|waiting_parts|completed|cancelled|invoiced)$")
    description: Optional[str] = None
    mechanic_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    discount: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(None, ge=0)


class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(draft|pending|confirmed|in_progress|waiting_parts|completed|cancelled|invoiced)$")
    mechanic_notes: Optional[str] = None


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    customer_id: int
    mechanic_id: Optional[int] = None
    status: str
    total_price: float
    labor_cost: float
    parts_cost: float
    discount: float
    tax: float
    mechanic_notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class OrderWithRelations(OrderResponse):
    customer: "UserResponse"
    mechanic: Optional["UserResponse"] = None
    vehicle: "VehicleResponse"
    items: List[OrderItemResponse] = []


class OrderListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    customer_id: int
    customer_name: str
    vehicle_id: int
    vehicle_info: str
    mechanic_id: Optional[int] = None
    status: str
    total_price: float
    created_at: datetime