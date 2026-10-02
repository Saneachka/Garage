from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    vin: Mapped[str | None] = mapped_column(String(17), unique=True, nullable=True, index=True)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engine_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transmission: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="vehicles")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="vehicle", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="vehicle", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_vehicles_owner_plate", "owner_id", "license_plate"),
    )

    def __repr__(self):
        return f"<Vehicle(id={self.id}, make='{self.make}', model='{self.model}', plate='{self.license_plate}')>"