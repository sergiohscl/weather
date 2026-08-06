from datetime import UTC, datetime
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from weather.models.authenticate import RefreshToken
from weather.schemas.authenticate import TokenSchema
from weather.core.authenticate.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def invalid_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Credenciais inválidas.',
        headers={'WWW-Authenticate': 'Bearer'},
    )


async def create_token_pair(
    account_id: int,
    db: AsyncSession,
) -> TokenSchema:
    access_token = create_access_token(account_id)
    refresh_token = create_refresh_token(account_id)
    refresh_payload = decode_token(refresh_token, expected_type='refresh')
    expires_at = datetime.fromtimestamp(refresh_payload['exp'], UTC)

    db.add(
        RefreshToken(
            jti=refresh_payload['jti'],
            account_id=account_id,
            expires_at=expires_at,
        )
    )

    return TokenSchema(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def get_active_refresh_token(
    token: str,
    db: AsyncSession,
) -> tuple[dict, RefreshToken]:
    try:
        payload = decode_token(token, expected_type='refresh')
    except ValueError as error:
        raise invalid_credentials_exception() from error

    refresh_token = await db.scalar(
        select(RefreshToken).where(RefreshToken.jti == payload['jti'])
    )
    if refresh_token is None or refresh_token.revoked_at is not None:
        raise invalid_credentials_exception()

    return payload, refresh_token
