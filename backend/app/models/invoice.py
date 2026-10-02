import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, Numeric, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_PAY = "mobile_pay"
    OTHER = "other"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    tax: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    discount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="invoices")
    customer: Mapped["User"] = relationship("User")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_invoices_customer_status", "customer_id", "status"),
        Index("ix_invoices_due_date", "due_date"),
    )

    @property
    def balance_due(self) -> float:
        return float(self.total) - float(self.paid_amount)

    def __repr__(self):
        return f"<Invoice(id={self.id}, number='{self.invoice_number}', total={self.total})>"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")

    __table_args__ = (
        Index("ix_payments_invoice_status", "invoice_id", "status"),
        Index("ix_payments_transaction_id", "transaction_id"),
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount}, method={self.method})>"