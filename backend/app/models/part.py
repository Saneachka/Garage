from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Numeric, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    service_type_id: Mapped[int | None] = mapped_column(ForeignKey("service_types.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    part_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    sale_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    quantity_in_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_stock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    unit: Mapped[str] = mapped_column(String(50), nullable=False, default="pcs")  # pcs, liters, kg, etc.
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)  # warehouse location
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    service_type: Mapped["ServiceType | None"] = relationship("ServiceType", back_populates="parts")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="part")
    stock_movements: Mapped[list["StockMovement"]] = relationship("StockMovement", back_populates="part", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_parts_category_active", "category", "is_active"),
        Index("ix_parts_stock_level", "quantity_in_stock", "min_stock_level"),
    )

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_in_stock <= self.min_stock_level

    def __repr__(self):
        return f"<Part(id={self.id}, name='{self.name}', part_number='{self.part_number}', stock={self.quantity_in_stock})>"


class StockMovementType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    TRANSFER = "transfer"


import enum


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type: Mapped[StockMovementType] = mapped_column(Enum(StockMovementType), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # order, purchase, adjustment, etc.
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    part: Mapped["Part"] = relationship("Part", back_populates="stock_movements")

    __table_args__ = (
        Index("ix_stock_movements_part_created", "part_id", "created_at"),
        Index("ix_stock_movements_reference", "reference_type", "reference_id"),
    )

    def __repr__(self):
        return f"<StockMovement(id={self.id}, part_id={self.part_id}, type={self.movement_type}, qty={self.quantity})>"