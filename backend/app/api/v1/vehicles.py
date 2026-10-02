from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse, VehicleWithOrders
from app.api.deps import get_current_active_user, require_mechanic


router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if license plate already exists for this user
    result = await db.execute(
        select(Vehicle).where(
            Vehicle.owner_id == current_user.id,
            Vehicle.license_plate == vehicle_data.license_plate
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Vehicle with this license plate already exists")

    if vehicle_data.vin:
        result = await db.execute(select(Vehicle).where(Vehicle.vin == vehicle_data.vin))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vehicle with this VIN already exists")

    vehicle = Vehicle(**vehicle_data.model_dump(), owner_id=current_user.id)
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleResponse])
async def list_vehicles(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role.value in ["admin", "manager", "mechanic"]:
        result = await db.execute(select(Vehicle).offset(skip).limit(limit))
    else:
        result = await db.execute(
            select(Vehicle).where(Vehicle.owner_id == current_user.id).offset(skip).limit(limit)
        )
    return result.scalars().all()


@router.get("/{vehicle_id}", response_model=VehicleWithOrders)
async def get_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Vehicle).options(
        selectinload(Vehicle.orders),
        selectinload(Vehicle.appointments)
    ).where(Vehicle.id == vehicle_id)
    result = await db.execute(query)
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Check ownership
    if current_user.role.value not in ["admin", "manager", "mechanic"] and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this vehicle")

    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if current_user.role.value not in ["admin", "manager", "mechanic"] and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this vehicle")

    if vehicle_update.license_plate and vehicle_update.license_plate != vehicle.license_plate:
        result = await db.execute(
            select(Vehicle).where(
                Vehicle.owner_id == vehicle.owner_id,
                Vehicle.license_plate == vehicle_update.license_plate,
                Vehicle.id != vehicle_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vehicle with this license plate already exists")

    if vehicle_update.vin and vehicle_update.vin != vehicle.vin:
        result = await db.execute(select(Vehicle).where(Vehicle.vin == vehicle_update.vin, Vehicle.id != vehicle_id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vehicle with this VIN already exists")

    update_data = vehicle_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if current_user.role.value not in ["admin", "manager"] and vehicle.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this vehicle")

    await db.delete(vehicle)
    await db.commit()