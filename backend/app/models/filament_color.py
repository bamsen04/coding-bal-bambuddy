from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class FilamentColorEntry(Base):
    """A user-managed filament color, independent of the Filament/Inventory catalogs."""

    __tablename__ = "filament_colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    color_name: Mapped[str] = mapped_column(String(200))
    hex_color: Mapped[str] = mapped_column(String(9))  # #RRGGBB or #RRGGBBAA
    filament_type: Mapped[str] = mapped_column(String(50))  # PLA, PETG, ABS, TPU, etc.
    brand: Mapped[str] = mapped_column(String(100))  # Generic, Bambu Lab, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
