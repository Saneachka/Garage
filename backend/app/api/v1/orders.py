from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from app.db.session import get_db
from app.models.order import Order, OrderItem, OrderStatus
from app.models.vehicle import Vehicle
from app.models.user import User
from app.models.service_type import ServiceType
from app.models.part import Part
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderStatusUpdate, OrderResponse, 
    OrderWithRelations, OrderListResponse, OrderItemCreate
)
from app.api.deps import get_current_active_user, require_mechanic, require_manager


router = APIRouter(prefix="/orders", tags=["Orders"])


def generate_order_number() -> str:
    from datetime import datetime
    import random
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


@router.post("", response_model=OrderWithRelations, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify vehicle exists and belongs to user (or user is staff)
    result = await db.execute(select(Vehicle).where(Vehicle.id == order_data.vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if current_user.role.value not in ["admin", "manager", "mechanic"] and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create order for this vehicle")

    # Create order
    order = Order(
        order_number=generate_order_number(),
        customer_id=current_user.id if current_user.role.value == "customer" else order_data.customer_id if hasattr(order_data, 'customer_id') else current_user.id,
        vehicle_id=order_data.vehicle_id,
        description=order_data.description,
        customer_notes=order_data.customer_notes,
        status=OrderStatus.DRAFT,
    )
    db.add(order)
    await db.flush()

    # Create order items
    total_price = 0
    labor_cost = 0
    parts_cost = 0

    for item_data in order_data.items:
        unit_price = item_data.unit_price
        total_item_price = unit_price * item_data.quantity

        if item_data.service_type_id:
            result = await db.execute(select(ServiceType).where(ServiceType.id == item_data.service_type_id))
            service_type = result.scalar_one_or_none()
            if not service_type:
                raise HTTPException(status_code=404, detail=f"Service type {item_data.service_type_id} not found")
            if unit_price == 0:
                unit_price = float(service_type.base_price)
                total_item_price = unit_price * item_data.quantity

        if item_data.part_id:
            result = await db.execute(select(Part).where(Part.id == item_data.part_id))
            part = result.scalar_one_or_none()
            if not part:
                raise HTTPException(status_code=404, detail=f"Part {item_data.part_id} not found")
            if unit_price == 0:
                unit_price = float(part.sale_price)
                total_item_price = unit_price * item_data.quantity
            # Check stock
            if part.quantity_in_stock < item_data.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for part {part.name}")

        item = OrderItem(
            order_id=order.id,
            service_type_id=item_data.service_type_id,
            part_id=item_data.part_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            total_price=total_item_price,
            description=item_data.description,
            is_labor=item_data.is_labor or bool(item_data.service_type_id),
        )
        db.add(item)
        total_price += total_item_price
        if item.is_labor:
            labor_cost += total_item_price
        else:
            parts_cost += total_item_price

    order.total_price = total_price
    order.labor_cost = labor_cost
    order.parts_cost = parts_cost

    await db.commit()
    
    # Reload with relations
    query = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.mechanic),
        selectinload(Order.vehicle),
        selectinload(Order.items).selectinload(OrderItem.service_type),
        selectinload(Order.items).selectinload(OrderItem.part),
    ).where(Order.id == order.id)
    result = await db.execute(query)
    return result.scalar_one()


@router.get("", response_model=list[OrderListResponse])
async def list_orders(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    mechanic_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(
        Order.id,
        Order.order_number,
        Order.customer_id,
        User.full_name.label("customer_name"),
        Order.vehicle_id,
        (Vehicle.make + " " + Vehicle.model + " (" + Vehicle.license_plate + ")").label("vehicle_info"),
        Order.mechanic_id,
        Order.status,
        Order.total_price,
        Order.created_at,
    ).join(User, Order.customer_id == User.id).join(Vehicle, Order.vehicle_id == Vehicle.id)

    if current_user.role.value == "customer":
        query = query.where(Order.customer_id == current_user.id)
    elif current_user.role.value == "mechanic":
        query = query.where((Order.mechanic_id == current_user.id) | (Order.customer_id == current_user.id))

    if status:
        query = query.where(Order.status == status)
    if customer_id and current_user.role.value in ["admin", "manager"]:
        query = query.where(Order.customer_id == customer_id)
    if mechanic_id and current_user.role.value in ["admin", "manager"]:
        query = query.where(Order.mechanic_id == mechanic_id)
    if vehicle_id:
        query = query.where(Order.vehicle_id == vehicle_id)

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.mappings().all()


@router.get("/{order_id}", response_model=OrderWithRelations)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).options(
        selectinload(Order.customer),
        selectinload(Order.mechanic),
        selectinload(Order.vehicle),
        selectinload(Order.items).selectinload(OrderItem.service_type),
        selectinload(Order.items).selectinload(OrderItem.part),
    ).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role.value == "customer" and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    if current_user.role.value == "mechanic" and order.mechanic_id != current_user.id and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")

    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Permission checks
    if current_user.role.value == "customer" and order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this order")
    if current_user.role.value == "mechanic" and order.mechanic_id != current_user.id:
        if order_update.status or order_update.mechanic_id:
            raise HTTPException(status_code=403, detail="Mechanics can only update notes")

    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)

    # Set started_at when status changes to in_progress
    if order_update.status == OrderStatus.IN_PROGRESS and not order.started_at:
        order.started_at = datetime.utcnow()
    # Set completed_at when status changes to completed
    if order_update.status == OrderStatus.COMPLETED and not order.completed_at:
        order.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(require_mechanic),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Assign mechanic if not assigned
    if not order.mechanic_id:
        order.mechanic_id = current_user.id

    old_status = order.status
    order.status = OrderStatus(status_update.status)

    if status_update.mechanic_notes:
        order.mechanic_notes = status_update.mechanic_notes

    # Set timestamps
    if status_update.status == OrderStatus.IN_PROGRESS and not order.started_at:
        order.started_at = datetime.utcnow()
    if status_update.status == OrderStatus.COMPLETED and not order.completed_at:
        order.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in [OrderStatus.DRAFT, OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Can only delete draft or cancelled orders")

    await db.delete(order)
    await db.commit()