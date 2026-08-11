from pydantic import BaseModel, Field


class WeatherCitySchema(BaseModel):
    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description='Nome da cidade para consulta do clima',
        examples=['Brasília'],
    )
