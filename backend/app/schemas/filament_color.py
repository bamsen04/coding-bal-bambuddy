from datetime import datetime

from pydantic import BaseModel, Field

_HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"


class FilamentColorCreate(BaseModel):
    color_name: str
    hex_color: str = Field(..., pattern=_HEX_COLOR_PATTERN)
    filament_type: str
    brand: str


class FilamentColorResponse(BaseModel):
    id: int
    color_name: str
    hex_color: str
    filament_type: str
    brand: str
    created_at: datetime

    class Config:
        from_attributes = True
