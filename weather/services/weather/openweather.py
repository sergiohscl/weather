from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.settings import settings
from weather.models.weather.weather_log import WeatherLog


class OpenWeatherService:
    """Serviço responsável pela integração com a OpenWeather API."""

    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY.get_secret_value()
        self.base_url = settings.OPENWEATHER_BASE_URL
        self.geocoding_url = settings.OPENWEATHER_GEOCODING_URL
        self.units = settings.OPENWEATHER_UNITS
        self.lang = settings.OPENWEATHER_LANG

    async def geocode_city(
        self,
        city_name: str,
        country_code: str = 'BR',
    ) -> tuple[float, float, str]:
        params = {
            'q': f'{city_name},{country_code}',
            'limit': 1,
            'appid': self.api_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.geocoding_url,
                params=params,
            )

        response.raise_for_status()

        data = response.json()

        if not data:
            raise ValueError(
                f"Cidade '{city_name}' não encontrada na API de geocoding."
            )

        item = data[0]

        lat = float(item['lat'])
        lon = float(item['lon'])
        name = item.get('name') or city_name

        return lat, lon, name

    async def fetch_current_weather(
        self,
        *,
        lat: float | None = None,
        lon: float | None = None,
    ) -> dict[str, Any]:
        latitude = lat if lat is not None else settings.OPENWEATHER_LAT

        longitude = lon if lon is not None else settings.OPENWEATHER_LON

        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': self.units,
            'lang': self.lang,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.base_url,
                params=params,
            )

        response.raise_for_status()

        data = response.json()

        payload = {
            'timestamp': datetime.now(timezone.utc),
            'city': data.get('name') or 'Desconhecida',
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed'],
            'condition': data['weather'][0]['description'],
            'raw': data,
        }

        return payload

    async def store_current_weather(
        self,
        session: AsyncSession,
        *,
        lat: float | None = None,
        lon: float | None = None,
    ) -> WeatherLog:
        payload = await self.fetch_current_weather(
            lat=lat,
            lon=lon,
        )

        weather_log = WeatherLog(**payload)

        session.add(weather_log)

        await session.commit()
        await session.refresh(weather_log)

        return weather_log

    async def store_weather_for_city(
        self,
        session: AsyncSession,
        city_name: str,
        country_code: str = 'BR',
    ) -> WeatherLog:
        lat, lon, normalized_name = await self.geocode_city(
            city_name,
            country_code=country_code,
        )

        payload = await self.fetch_current_weather(
            lat=lat,
            lon=lon,
        )

        payload['city'] = normalized_name

        weather_log = WeatherLog(**payload)

        session.add(weather_log)

        await session.commit()
        await session.refresh(weather_log)

        return weather_log


openweather_service = OpenWeatherService()
