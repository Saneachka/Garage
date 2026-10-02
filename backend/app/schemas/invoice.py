from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.order import OrderResponse


class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    method: str = Field(..., pattern="^(cash|card|bank_transfer|mobile_pay|other)$")
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    status: str
    transaction_id: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime


class InvoiceBase(BaseModel):
    order_id: int
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    discount: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(draft|sent|paid|partially_paid|overdue|cancelled|refunded)$")


class InvoiceResponse(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    customer_id: int
    status: str
    subtotal: float
    tax: float
    discount: float
    total: float
    paid_amount: float
    issued_at: datetime
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @property
    def balance_due(self) -> float:
        return self.total - self.paid_amount


class InvoiceWithRelations(InvoiceResponse):
    customer: "UserResponse"
    order: OrderResponse
    payments: List[PaymentResponse] = []


class InvoiceListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    customer_id: int
    customer_name: str
    order_id: int
    order_number: str
    status: str
    total: float
    paid_amount: float
    balance_due: float
    due_date: Optional[datetime] = None
    issued_at: datetime