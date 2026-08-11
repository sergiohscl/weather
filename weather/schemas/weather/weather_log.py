from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class WeatherLogBase(BaseModel):
    timestamp: datetime
    city: str
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    condition: str
    raw: dict[str, Any] | None = None


class WeatherLogCreate(WeatherLogBase):
    pass


class WeatherLogUpdate(BaseModel):
    timestamp: datetime | None = None
    city: str | None = None
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    wind_speed: float | None = None
    condition: str | None = None
    raw: dict[str, Any] | None = None


class WeatherLogResponse(WeatherLogBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeatherLogListResponse(BaseModel):
    items: list[WeatherLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


WeatherLogSortField = Literal[
    'id',
    'timestamp',
    'city',
    'temperature',
    'humidity',
    'pressure',
    'wind_speed',
    'condition',
    'created_at',
]

WeatherLogSortOrder = Literal['asc', 'desc']
