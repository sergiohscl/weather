from pydantic import BaseModel


class WeatherTaskResponseSchema(BaseModel):
    message: str
    task_id: str
