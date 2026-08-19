import asyncio
import logging

from weather.core.database import AsyncSessionLocal
from weather.models.weather.weather_insight import WeatherInsight
from weather.services.weather.weather_service import WeatherService
from weather.tasks.weather.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _collect_weather(city: str):
    async with AsyncSessionLocal() as session:
        service = WeatherService(session)

        log = await service.collect_current_weather(
            city=city,
        )

        logger.info(
            'WeatherLog criado com id=%s para %s',
            log.id,
            log.city,
        )

        return log.id


@celery_app.task(
    name='weather.collect_current_weather',
)
def collect_current_weather(city: str):
    return asyncio.run(_collect_weather(city))


async def _generate_weather_insight(
    hours: int = 24,
    city: str | None = None,
):
    async with AsyncSessionLocal() as session:
        service = WeatherService(session)

        logger.info(
            'Iniciando geração de insight hours=%s city=%s',
            hours,
            city,
        )

        insight_text = await service.generate_insight(
            hours=hours,
            city=city,
        )

        weather_insight = WeatherInsight(
            city=city or '',
            text=insight_text,
        )

        session.add(weather_insight)

        await session.commit()
        await session.refresh(weather_insight)

        logger.info(
            'WeatherInsight criado com id=%s',
            weather_insight.id,
        )

        return {
            'id': weather_insight.id,
            'city': weather_insight.city,
            'generated_at': weather_insight.generated_at,
            'text': weather_insight.text,
        }


@celery_app.task(
    name='weather.generate_weather_insight',
)
def generate_weather_insight(
    hours: int = 24,
    city: str | None = None,
):
    return asyncio.run(
        _generate_weather_insight(
            hours=hours,
            city=city,
        )
    )
