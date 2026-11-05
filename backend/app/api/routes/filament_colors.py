from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import RequirePermissionIfAuthEnabled
from backend.app.core.database import get_db
from backend.app.core.permissions import Permission
from backend.app.models.filament_color import FilamentColorEntry
from backend.app.models.user import User
from backend.app.schemas.filament_color import FilamentColorCreate, FilamentColorResponse

router = APIRouter(prefix="/filament-colors", tags=["filament-colors"])


@router.get("/", response_model=list[FilamentColorResponse])
async def list_filament_colors(
    db: AsyncSession = Depends(get_db),
    _: User | None = RequirePermissionIfAuthEnabled(Permission.FILAMENT_COLORS_VIEW),
):
    """List all filament color entries."""
    result = await db.execute(
        select(FilamentColorEntry).order_by(FilamentColorEntry.filament_type, FilamentColorEntry.color_name)
    )
    return list(result.scalars().all())


@router.post("/", response_model=FilamentColorResponse)
async def create_filament_color(
    data: FilamentColorCreate,
    db: AsyncSession = Depends(get_db),
    _: User | None = RequirePermissionIfAuthEnabled(Permission.FILAMENT_COLORS_VIEW),
):
    """Create a new filament color entry."""
    entry = FilamentColorEntry(**data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}")
async def delete_filament_color(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _: User | None = RequirePermissionIfAuthEnabled(Permission.FILAMENT_COLORS_VIEW),
):
    """Delete a filament color entry."""
    result = await db.execute(select(FilamentColorEntry).where(FilamentColorEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Filament color not found")

    await db.delete(entry)
    await db.commit()
    return {"status": "deleted"}
