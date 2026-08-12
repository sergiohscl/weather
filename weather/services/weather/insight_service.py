from datetime import datetime, timedelta

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

        # Não existem dados para gerar insight
        if not weather_logs:
            return base_text

        # OpenAI desabilitada
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

        # ---------------------------------------------------------
        # SQLite está armazenando os timestamps sem timezone.
        # Por isso trabalhamos aqui com datetime naive.
        # ---------------------------------------------------------

        since = datetime.utcnow() - timedelta(hours=hours)

        query = select(WeatherLog).where(WeatherLog.timestamp >= since)

        # ---------------------------------------------------------
        # Filtro da cidade
        #
        # Antes:
        #     ilike(city)
        #
        # Agora:
        #     ilike("%cidade%")
        #
        # Isso também deixa a busca mais flexível.
        # ---------------------------------------------------------

        if city and city.strip():
            city_filter = city.strip()

            query = query.where(WeatherLog.city.ilike(f'%{city_filter}%'))

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

        # ---------------------------------------------------------
        # Nenhum registro encontrado
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # Dados encontrados
        # ---------------------------------------------------------

        temperatures = [
            weather.temperature
            for weather in logs
            if weather.temperature is not None
        ]

        humidities = [
            weather.humidity
            for weather in logs
            if weather.humidity is not None
        ]

        wind_speeds = [
            weather.wind_speed
            for weather in logs
            if weather.wind_speed is not None
        ]

        # ---------------------------------------------------------
        # Proteção caso algum campo esteja vazio
        # ---------------------------------------------------------

        if not temperatures:
            return (
                f'Foram encontrados {count} registros climáticos '
                f'para {city or "a cidade solicitada"}, '
                'mas não há dados de temperatura suficientes.'
            )

        # ---------------------------------------------------------
        # Estatísticas
        # ---------------------------------------------------------

        max_temperature = max(temperatures)
        min_temperature = min(temperatures)
        avg_temperature = sum(temperatures) / len(temperatures)

        avg_humidity = sum(humidities) / len(humidities) if humidities else 0

        avg_wind = sum(wind_speeds) / len(wind_speeds) if wind_speeds else 0

        # Como a query está DESC, o primeiro é o mais recente.
        last = logs[0]

        city_reference = city or last.city

        # ---------------------------------------------------------
        # Detecta tendência simples de temperatura
        # ---------------------------------------------------------

        temperature_trend = 'estável'

        if len(temperatures) >= 2:
            newest_temperature = temperatures[0]
            oldest_temperature = temperatures[-1]

            difference = newest_temperature - oldest_temperature

            if difference >= 1:
                temperature_trend = 'de aquecimento'

            elif difference <= -1:
                temperature_trend = 'de resfriamento'

        # ---------------------------------------------------------
        # Insight numérico
        # ---------------------------------------------------------

        return (
            f'Nas últimas {hours}h, foram coletadas '
            f'{count} medições em {city_reference}.\n'
            f'A temperatura apresenta tendência '
            f'{temperature_trend}, com média de '
            f'{avg_temperature:.1f}°C '
            f'(máx {max_temperature:.1f}°C, '
            f'mín {min_temperature:.1f}°C).\n'
            f'A umidade média está em '
            f'{avg_humidity:.0f}% e o vento médio '
            f'em {avg_wind:.1f} m/s.\n'
            f'A condição mais recente em {last.city} '
            f'é {last.condition}, com '
            f'{last.temperature:.1f}°C.'
        )

    @staticmethod
    async def _generate_openai_insight(
        logs: list[WeatherLog],
        base_text: str,
        city: str | None = None,
    ) -> str:

        # Pegamos somente as 5 medições mais recentes
        recent_logs = logs[:5]

        lines = []

        for weather in recent_logs:
            lines.append(
                f'- {weather.timestamp:%d/%m %H:%M} | '
                f'{weather.city} | '
                f'{weather.temperature:.1f}°C | '
                f'{weather.humidity:.0f}% umidade | '
                f'{weather.wind_speed:.1f} m/s vento | '
                f'{weather.condition}'
            )

        summary = '\n'.join(lines)

        city_reference = city or recent_logs[0].city

        prompt = (
            'Você é um especialista em meteorologia '
            'explicando dados de clima para um usuário leigo.\n\n'
            f'A cidade foco é: {city_reference}.\n\n'
            'Use o resumo numérico e as últimas medições '
            'abaixo para gerar um texto curto '
            '(máximo de 6 frases), em português do Brasil, '
            'com tom claro, natural e amigável.\n\n'
            'Foque em tendências como:\n'
            '- aquecimento\n'
            '- resfriamento\n'
            '- estabilidade\n'
            '- umidade\n'
            '- vento\n'
            '- condição climática\n\n'
            'Também apresente uma recomendação prática '
            'quando fizer sentido.\n\n'
            'Não invente dados que não estejam presentes '
            'nas medições.\n\n'
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
                            'em meteorologia. '
                            'Gere comentários curtos, '
                            'úteis e baseados exclusivamente '
                            'nos dados fornecidos.'
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
