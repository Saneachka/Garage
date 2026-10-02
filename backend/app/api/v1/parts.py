from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.part import Part, StockMovement, StockMovementType
from app.models.service_type import ServiceType
from app.schemas.part import (
    PartCreate, PartUpdate, PartResponse, PartWithServiceType, PartWithMovements,
    StockMovementCreate, StockMovementResponse
)
from app.api.deps import get_current_active_user, require_manager


router = APIRouter(prefix="/parts", tags=["Parts"])


@router.post("", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
async def create_part(
    part_data: PartCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    # Check part number uniqueness
    result = await db.execute(select(Part).where(Part.part_number == part_data.part_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Part number already exists")

    # Verify service type if provided
    if part_data.service_type_id:
        result = await db.execute(select(ServiceType).where(ServiceType.id == part_data.service_type_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Service type not found")

    part = Part(**part_data.model_dump())
    db.add(part)
    await db.commit()
    await db.refresh(part)
    return part


@router.get("", response_model=list[PartResponse])
async def list_parts(
    category: Optional[str] = None,
    service_type_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    low_stock_only: bool = False,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Part)

    if category:
        query = query.where(Part.category == category)
    if service_type_id:
        query = query.where(Part.service_type_id == service_type_id)
    if is_active is not None:
        query = query.where(Part.is_active == is_active)
    if low_stock_only:
        query = query.where(Part.quantity_in_stock <= Part.min_stock_level)
    if search:
        query = query.where(
            (Part.name.ilike(f"%{search}%")) |
            (Part.part_number.ilike(f"%{search}%")) |
            (Part.manufacturer.ilike(f"%{search}%"))
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories", response_model=list[str])
async def get_part_categories(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Part.category).distinct())
    return [row[0] for row in result.all()]


@router.get("/low-stock", response_model=list[PartResponse])
async def get_low_stock_parts(
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Part).where(Part.quantity_in_stock <= Part.min_stock_level, Part.is_active == True)
    )
    return result.scalars().all()


@router.get("/{part_id}", response_model=PartWithServiceType)
async def get_part(
    part_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Part).options(selectinload(Part.service_type)).where(Part.id == part_id)
    result = await db.execute(query)
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return part


@router.get("/{part_id}/movements", response_model=list[StockMovementResponse])
async def get_part_movements(
    part_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.part_id == part_id)
        .order_by(StockMovement.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.patch("/{part_id}", response_model=PartResponse)
async def update_part(
    part_id: int,
    part_update: PartUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    if part_update.part_number and part_update.part_number != part.part_number:
        result = await db.execute(select(Part).where(Part.part_number == part_update.part_number, Part.id != part_id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Part number already exists")

    if part_update.service_type_id:
        result = await db.execute(select(ServiceType).where(ServiceType.id == part_update.service_type_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Service type not found")

    update_data = part_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(part, field, value)

    await db.commit()
    await db.refresh(part)
    return part


@router.post("/{part_id}/stock", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
async def add_stock_movement(
    part_id: int,
    movement_data: StockMovementCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    # Validate quantity for OUT movements
    if movement_data.movement_type == StockMovementType.OUT:
        if part.quantity_in_stock < movement_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

    movement = StockMovement(
        part_id=part_id,
        movement_type=StockMovementType(movement_data.movement_type),
        quantity=movement_data.quantity,
        reference_type=movement_data.reference_type,
        reference_id=movement_data.reference_id,
        notes=movement_data.notes,
    )
    db.add(movement)

    # Update part stock
    if movement_data.movement_type == StockMovementType.IN:
        part.quantity_in_stock += movement_data.quantity
    elif movement_data.movement_type == StockMovementType.OUT:
        part.quantity_in_stock -= movement_data.quantity
    elif movement_data.movement_type == StockMovementType.ADJUSTMENT:
        part.quantity_in_stock = movement_data.quantity
    elif movement_data.movement_type == StockMovementType.RETURN:
        part.quantity_in_stock += movement_data.quantity

    await db.commit()
    await db.refresh(movement)
    return movement


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_part(
    part_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Part).where(Part.id == part_id))
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    # Soft delete
    part.is_active = False
    await db.commit()