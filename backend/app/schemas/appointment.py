from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AppointmentBase(BaseModel):
    vehicle_id: int
    scheduled_at: datetime
    estimated_duration_minutes: int = Field(..., ge=15, le=480)
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    order_id: Optional[int] = None


class AppointmentUpdate(BaseModel):
    vehicle_id: Optional[int] = None
    order_id: Optional[int] = None
    mechanic_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(scheduled|confirmed|in_progress|completed|cancelled|no_show)$")
    scheduled_at: Optional[datetime] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(scheduled|confirmed|in_progress|completed|cancelled|no_show)$")
    cancellation_reason: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    order_id: Optional[int] = None
    mechanic_id: Optional[int] = None
    status: str
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AppointmentWithRelations(AppointmentResponse):
    customer: "UserResponse"
    vehicle: "VehicleResponse"
    order: Optional["OrderResponse"] = None
    mechanic: Optional["UserResponse"] = None