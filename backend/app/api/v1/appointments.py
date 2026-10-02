from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.vehicle import Vehicle
from app.models.user import User
from app.models.order import Order
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentStatusUpdate,
    AppointmentResponse, AppointmentWithRelations
)
from app.api.deps import get_current_active_user, require_mechanic, require_manager


router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("", response_model=AppointmentWithRelations, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify vehicle
    result = await db.execute(select(Vehicle).where(Vehicle.id == appointment_data.vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if current_user.role.value not in ["admin", "manager", "mechanic"] and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create appointment for this vehicle")

    # Verify order if provided
    if appointment_data.order_id:
        result = await db.execute(select(Order).where(Order.id == appointment_data.order_id))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.vehicle_id != appointment_data.vehicle_id:
            raise HTTPException(status_code=400, detail="Order vehicle doesn't match appointment vehicle")

    # Check for conflicting appointments
    end_time = appointment_data.scheduled_at + timedelta(minutes=appointment_data.estimated_duration_minutes)
    result = await db.execute(
        select(Appointment).where(
            Appointment.mechanic_id == appointment_data.mechanic_id if appointment_data.mechanic_id else Appointment.mechanic_id.is_(None),
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]),
            Appointment.scheduled_at < end_time,
            Appointment.scheduled_at + func.make_interval(mins=Appointment.estimated_duration_minutes) > appointment_data.scheduled_at,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Time slot not available")

    appointment = Appointment(
        customer_id=current_user.id if current_user.role.value == "customer" else appointment_data.customer_id if hasattr(appointment_data, 'customer_id') else current_user.id,
        vehicle_id=appointment_data.vehicle_id,
        order_id=appointment_data.order_id,
        mechanic_id=appointment_data.mechanic_id,
        scheduled_at=appointment_data.scheduled_at,
        estimated_duration_minutes=appointment_data.estimated_duration_minutes,
        notes=appointment_data.notes,
        status=AppointmentStatus.SCHEDULED,
    )
    db.add(appointment)
    await db.commit()

    # Reload with relations
    query = select(Appointment).options(
        selectinload(Appointment.customer),
        selectinload(Appointment.vehicle),
        selectinload(Appointment.order),
        selectinload(Appointment.mechanic),
    ).where(Appointment.id == appointment.id)
    result = await db.execute(query)
    return result.scalar_one()


@router.get("", response_model=list[AppointmentWithRelations])
async def list_appointments(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    mechanic_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Appointment).options(
        selectinload(Appointment.customer),
        selectinload(Appointment.vehicle),
        selectinload(Appointment.order),
        selectinload(Appointment.mechanic),
    )

    if current_user.role.value == "customer":
        query = query.where(Appointment.customer_id == current_user.id)
    elif current_user.role.value == "mechanic":
        query = query.where((Appointment.mechanic_id == current_user.id) | (Appointment.customer_id == current_user.id))

    if status:
        query = query.where(Appointment.status == status)
    if customer_id and current_user.role.value in ["admin", "manager"]:
        query = query.where(Appointment.customer_id == customer_id)
    if mechanic_id and current_user.role.value in ["admin", "manager"]:
        query = query.where(Appointment.mechanic_id == mechanic_id)
    if vehicle_id:
        query = query.where(Appointment.vehicle_id == vehicle_id)
    if start_date:
        query = query.where(Appointment.scheduled_at >= start_date)
    if end_date:
        query = query.where(Appointment.scheduled_at <= end_date)

    query = query.order_by(Appointment.scheduled_at).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/calendar", response_model=list[AppointmentWithRelations])
async def get_calendar(
    start_date: datetime,
    end_date: datetime,
    mechanic_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role.value not in ["admin", "manager", "mechanic"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = select(Appointment).options(
        selectinload(Appointment.customer),
        selectinload(Appointment.vehicle),
        selectinload(Appointment.order),
        selectinload(Appointment.mechanic),
    ).where(
        Appointment.scheduled_at >= start_date,
        Appointment.scheduled_at <= end_date,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]),
    )

    if mechanic_id:
        query = query.where(Appointment.mechanic_id == mechanic_id)
    elif current_user.role.value == "mechanic":
        query = query.where(Appointment.mechanic_id == current_user.id)

    query = query.order_by(Appointment.scheduled_at)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{appointment_id}", response_model=AppointmentWithRelations)
async def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Appointment).options(
        selectinload(Appointment.customer),
        selectinload(Appointment.vehicle),
        selectinload(Appointment.order),
        selectinload(Appointment.mechanic),
    ).where(Appointment.id == appointment_id)
    result = await db.execute(query)
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role.value == "customer" and appointment.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role.value == "mechanic" and appointment.mechanic_id != current_user.id and appointment.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role.value == "customer" and appointment.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if current_user.role.value == "mechanic" and appointment.mechanic_id != current_user.id:
        if appointment_update.status or appointment_update.mechanic_id:
            raise HTTPException(status_code=403, detail="Mechanics can only update notes")

    update_data = appointment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    # Check for conflicts if time/mechanic changed
    if appointment_update.scheduled_at or appointment_update.mechanic_id or appointment_update.estimated_duration_minutes:
        end_time = appointment.scheduled_at + timedelta(minutes=appointment.estimated_duration_minutes)
        conflict_query = select(Appointment).where(
            Appointment.id != appointment_id,
            Appointment.mechanic_id == appointment.mechanic_id,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]),
            Appointment.scheduled_at < end_time,
            Appointment.scheduled_at + func.make_interval(mins=Appointment.estimated_duration_minutes) > appointment.scheduled_at,
        )
        conflict = await db.execute(conflict_query)
        if conflict.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Time slot not available")

    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: int,
    status_update: AppointmentStatusUpdate,
    current_user: User = Depends(require_mechanic),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    old_status = appointment.status
    appointment.status = AppointmentStatus(status_update.status)

    if status_update.cancellation_reason:
        appointment.cancellation_reason = status_update.cancellation_reason

    # Set timestamps
    if status_update.status == AppointmentStatus.IN_PROGRESS and not appointment.actual_start_at:
        appointment.actual_start_at = datetime.utcnow()
    if status_update.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW] and not appointment.actual_end_at:
        appointment.actual_end_at = datetime.utcnow()

    # If appointment is linked to order, update order status
    if appointment.order_id and status_update.status == AppointmentStatus.IN_PROGRESS:
        order_result = await db.execute(select(Order).where(Order.id == appointment.order_id))
        order = order_result.scalar_one_or_none()
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.IN_PROGRESS
            order.started_at = datetime.utcnow()

    await db.commit()
    await db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role.value not in ["admin", "manager"] and appointment.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if appointment.status in [AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail="Cannot delete in-progress or completed appointment")

    await db.delete(appointment)
    await db.commit()