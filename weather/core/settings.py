from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    # JWT
    JWT_SECRET: SecretStr

    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OpenWeather
    OPENWEATHER_API_KEY: SecretStr
    OPENWEATHER_LAT: float = -15.7797
    OPENWEATHER_LON: float = -47.9297
    OPENWEATHER_UNITS: str = 'metric'
    OPENWEATHER_LANG: str = 'pt_br'

    OPENWEATHER_BASE_URL: str = (
        'https://api.openweathermap.org/data/2.5/weather'
    )

    OPENWEATHER_GEOCODING_URL: str = (
        'https://api.openweathermap.org/geo/1.0/direct'
    )

    # OpenAI
    OPENAI_API_KEY: SecretStr | None = None
    OPENAI_MODEL: str = 'gpt-4.1-mini'

    # Celery / RabbitMQ
    CELERY_BROKER_URL: str = 'amqp://guest:guest@rabbitmq:5672//'

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )


settings = Settings()
