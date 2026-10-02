from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.service_type import ServiceType
from app.models.part import Part
from app.schemas.service_type import ServiceTypeCreate, ServiceTypeUpdate, ServiceTypeResponse, ServiceTypeWithParts
from app.api.deps import get_current_active_user, require_manager


router = APIRouter(prefix="/service-types", tags=["Service Types"])


@router.post("", response_model=ServiceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_service_type(
    service_data: ServiceTypeCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    service_type = ServiceType(**service_data.model_dump())
    db.add(service_type)
    await db.commit()
    await db.refresh(service_type)
    return service_type


@router.get("", response_model=list[ServiceTypeResponse])
async def list_service_types(
    category: str | None = None,
    is_active: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ServiceType)
    if category:
        query = query.where(ServiceType.category == category)
    if is_active is not None:
        query = query.where(ServiceType.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories", response_model=list[str])
async def get_categories(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServiceType.category).distinct())
    return [row[0] for row in result.all()]


@router.get("/{service_type_id}", response_model=ServiceTypeWithParts)
async def get_service_type(
    service_type_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ServiceType).options(selectinload(ServiceType.parts)).where(ServiceType.id == service_type_id)
    result = await db.execute(query)
    service_type = result.scalar_one_or_none()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")
    return service_type


@router.patch("/{service_type_id}", response_model=ServiceTypeResponse)
async def update_service_type(
    service_type_id: int,
    service_update: ServiceTypeUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServiceType).where(ServiceType.id == service_type_id))
    service_type = result.scalar_one_or_none()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")

    update_data = service_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service_type, field, value)

    await db.commit()
    await db.refresh(service_type)
    return service_type


@router.delete("/{service_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_type(
    service_type_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ServiceType).where(ServiceType.id == service_type_id))
    service_type = result.scalar_one_or_none()
    if not service_type:
        raise HTTPException(status_code=404, detail="Service type not found")

    # Soft delete
    service_type.is_active = False
    await db.commit()