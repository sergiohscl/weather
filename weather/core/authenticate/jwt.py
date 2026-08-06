from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from weather.core.settings import settings


def create_token(
    account_id: int,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        'sub': str(account_id),
        'type': token_type,
        'jti': str(uuid4()),
        'iat': now,
        'exp': now + expires_delta,
    }
    secret = settings.JWT_SECRET.get_secret_value()

    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(account_id: int) -> str:
    return create_token(
        account_id,
        'access',
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(account_id: int) -> str:
    return create_token(
        account_id,
        'refresh',
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str) -> dict:
    secret = settings.JWT_SECRET.get_secret_value()
    try:
        payload = jwt.decode(
            token, secret, algorithms=[settings.JWT_ALGORITHM]
        )
    except InvalidTokenError as error:
        raise ValueError('Token inválido ou expirado.') from error

    if payload.get('type') != expected_type:
        raise ValueError('Tipo de token inválido.')

    return payload
