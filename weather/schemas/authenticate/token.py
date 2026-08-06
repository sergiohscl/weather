from pydantic import BaseModel


class LoginSchema(BaseModel):
    email: str
    password: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
