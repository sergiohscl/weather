from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from weather.core.database import Base


class WeatherInsight(Base):
    __tablename__ = 'weather_insights'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f'<WeatherInsight generated_at={self.generated_at!r}>'
