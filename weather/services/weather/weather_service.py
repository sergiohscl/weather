from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.models.weather.weather_insight import WeatherInsight
from weather.models.weather.weather_log import WeatherLog
from weather.services.weather.insight_service import InsightService
from weather.services.weather.openweather import OpenWeatherService


class WeatherService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.openweather = OpenWeatherService()
        self.insight = InsightService(session)

    async def fetch_city(
        self,
        city: str,
        country_code: str = 'BR',
    ) -> WeatherLog:
        return await self.openweather.store_weather_for_city(
            session=self.session,
            city_name=city,
            country_code=country_code,
        )

    async def collect_current_weather(
        self,
        city: str,
        country_code: str = 'BR',
    ) -> WeatherLog:
        return await self.fetch_city(
            city=city,
            country_code=country_code,
        )

    async def generate_insight(
        self,
        hours: int = 24,
        city: str | None = None,
    ) -> str:
        return await self.insight.generate_insight(
            hours=hours,
            city=city,
        )

    async def get_weather_logs(
        self,
        city: str | None = None,
        order: str = 'desc',
    ) -> list[WeatherLog]:
        query = select(WeatherLog)

        if city and city.strip():
            query = query.where(WeatherLog.city.ilike(f'%{city.strip()}%'))

        if order == 'asc':
            query = query.order_by(WeatherLog.timestamp.asc())
        else:
            query = query.order_by(WeatherLog.timestamp.desc())

        result = await self.session.scalars(query)

        return list(result.all())

    async def get_weather_log_by_id(
        self,
        weather_id: int,
    ) -> WeatherLog | None:
        return await self.session.scalar(
            select(WeatherLog).where(WeatherLog.id == weather_id)
        )

    async def delete_weather_log(
        self,
        weather_id: int,
    ) -> bool:
        weather_log = await self.get_weather_log_by_id(weather_id)

        if weather_log is None:
            return False

        await self.session.delete(weather_log)
        await self.session.commit()

        return True

    async def get_weather_insights(self) -> list[WeatherInsight]:
        result = await self.session.scalars(
            select(WeatherInsight).order_by(
                WeatherInsight.generated_at.desc()
            )
        )

        return list(result.all())
