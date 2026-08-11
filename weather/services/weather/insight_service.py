from datetime import datetime, timedelta, timezone

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.settings import settings
from weather.models.weather.weather_log import WeatherLog


class InsightService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_insight(
        self,
        hours: int = 24,
        city: str | None = None,
    ) -> str:
        weather_logs = await self._get_weather_logs(
            hours=hours,
            city=city,
        )

        base_text = self._generate_rule_based_insight(
            weather_logs,
            hours,
            city,
        )

        if not weather_logs:
            return base_text

        if not settings.OPENAI_API_KEY:
            return (
                f'{base_text}\n\n'
                '[IA desativada: OPENAI_API_KEY não configurada.]'
            )

        return await self._generate_openai_insight(
            weather_logs,
            base_text,
            city,
        )

    async def _get_weather_logs(
        self,
        hours: int,
        city: str | None = None,
    ) -> list[WeatherLog]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = select(WeatherLog).where(WeatherLog.timestamp >= since)

        if city:
            query = query.where(WeatherLog.city.ilike(city))

        query = query.order_by(WeatherLog.timestamp.desc())

        result = await self.session.execute(query)

        return list(result.scalars().all())

    @staticmethod
    def _generate_rule_based_insight(
        logs: list[WeatherLog],
        hours: int,
        city: str | None = None,
    ) -> str:
        count = len(logs)

        if count == 0:
            if city:
                return (
                    'Ainda não há dados suficientes para gerar '
                    f'insights climáticos para {city}.'
                )

            return (
                'Ainda não há dados suficientes para gerar '
                'insights climáticos.'
            )

        temperatures = [weather.temperature for weather in logs]

        humidities = [weather.humidity for weather in logs]

        max_temperature = max(temperatures)
        min_temperature = min(temperatures)
        avg_temperature = sum(temperatures) / len(temperatures)
        avg_humidity = sum(humidities) / len(humidities)

        last = logs[0]

        city_reference = city or last.city

        return (
            f'Nas últimas {hours}h, foram coletadas '
            f'{count} medições em {city_reference}.\n'
            f'Temperatura média: {avg_temperature:.1f}°C '
            f'(máx {max_temperature:.1f}°C, '
            f'mín {min_temperature:.1f}°C).\n'
            f'Umidade média: {avg_humidity:.0f}%.\n'
            f'Condição mais recente em {last.city}: '
            f'{last.condition} com '
            f'{last.temperature:.1f}°C e vento de '
            f'{last.wind_speed:.1f} m/s.'
        )

    @staticmethod
    async def _generate_openai_insight(
        logs: list[WeatherLog],
        base_text: str,
        city: str | None = None,
    ) -> str:
        recent_logs = logs[:5]

        lines = []

        for weather in recent_logs:
            lines.append(
                f'- {weather.timestamp:%d/%m %H:%M} | '
                f'{weather.city} | '
                f'{weather.temperature:.1f}°C | '
                f'{weather.humidity:.0f}% umidade | '
                f'{weather.condition}'
            )

        summary = '\n'.join(lines)

        city_reference = city or recent_logs[0].city

        prompt = (
            'Você é um especialista em meteorologia '
            'explicando dados de clima para um usuário leigo.\n'
            f'A cidade foco é: {city_reference}.\n'
            'Use o resumo numérico e as últimas medições '
            'abaixo para gerar um texto curto '
            '(máximo ~6 frases), em português do Brasil, '
            'com tom claro e amigável.\n'
            'Foque em tendências como aquecimento, '
            'resfriamento, estabilidade e umidade, '
            'além de recomendações práticas.\n\n'
            'Resumo numérico:\n'
            f'{base_text}\n\n'
            'Últimas medições:\n'
            f'{summary}\n\n'
            'Agora gere o insight.'
        )

        client = AsyncOpenAI(
            api_key=(settings.OPENAI_API_KEY.get_secret_value())
        )

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'Você é um assistente especializado '
                            'em clima, que gera comentários curtos '
                            'e úteis sobre o tempo atual e recente.'
                        ),
                    },
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ],
                temperature=0.4,
                max_tokens=300,
            )

            return (response.choices[0].message.content or '').strip()

        except Exception:
            return (
                f'{base_text}\n\n'
                '[Não foi possível gerar insight via IA '
                'no momento, exibindo resumo numérico.]'
            )

        finally:
            await client.close()
