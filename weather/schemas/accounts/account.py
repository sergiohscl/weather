from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountSchema(BaseModel):
    name: str
    email: str
    password: str


class AccountPublicSchema(BaseModel):
    id: int
    name: str
    email: str
    avatar: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountUpdateSchema(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    avatar: str | None = None


class AccountListPublicSchema(BaseModel):
    accounts: list[AccountPublicSchema]
