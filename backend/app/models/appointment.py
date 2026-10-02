import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    mechanic_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id], back_populates="appointments")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="appointments")
    order: Mapped["Order | None"] = relationship("Order", back_populates="appointments")
    mechanic: Mapped["User | None"] = relationship("User", foreign_keys=[mechanic_id])

    __table_args__ = (
        Index("ix_appointments_customer_scheduled", "customer_id", "scheduled_at"),
        Index("ix_appointments_mechanic_scheduled", "mechanic_id", "scheduled_at"),
        Index("ix_appointments_status_scheduled", "status", "scheduled_at"),
    )

    def __repr__(self):
        return f"<Appointment(id={self.id}, customer_id={self.customer_id}, scheduled_at={self.scheduled_at})>"