from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Numeric, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class ServiceType(Base):
    __tablename__ = "service_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., "Maintenance", "Repair", "Diagnostics"
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="service_type")
    parts: Mapped[list["Part"]] = relationship("Part", back_populates="service_type", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_service_types_category_active", "category", "is_active"),
    )

    def __repr__(self):
        return f"<ServiceType(id={self.id}, name='{self.name}', category='{self.category}')>"