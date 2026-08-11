from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WeatherInsightCreate(BaseModel):
    text: str


class WeatherInsightResponse(BaseModel):
    id: int
    generated_at: datetime
    text: str

    model_config = ConfigDict(from_attributes=True)


class WeatherInsightRequest(BaseModel):
    hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description='Quantidade de horas utilizadas para gerar o insight.',
    )

    city: str | None = Field(
        default=None,
        description='Cidade para análise. Exemplo: Brasília',
    )


class WeatherInsightTaskResponse(BaseModel):
    message: str = Field(
        description='Mensagem informando que a geração foi iniciada.'
    )

    task_id: str = Field(
        description='ID da tarefa Celery responsável pela geração do insight.'
    )

    hours: int = Field(
        description='Quantidade de horas utilizadas na análise.'
    )

    city: str | None = Field(
        default=None,
        description='Cidade utilizada na análise.',
    )
