from pydantic import BaseModel


class WeatherTaskResponseSchema(BaseModel):
    message: str
    task_id: str


class WeatherInsightTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None
