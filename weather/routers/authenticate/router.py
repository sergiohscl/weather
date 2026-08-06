from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.accounts.security import verify_password
from weather.core.authenticate.services import (
    create_token_pair,
    get_active_refresh_token,
    invalid_credentials_exception,
)
from weather.core.database import get_session
from weather.models.accounts import Account
from weather.schemas.authenticate import (
    LoginSchema,
    RefreshTokenSchema,
    TokenSchema,
)

router = APIRouter()


@router.post('/login', response_model=TokenSchema, summary='Fazer login')
async def login(
    data: LoginSchema,
    db: AsyncSession = Depends(get_session),
):
    account = await db.scalar(
        select(Account).where(Account.email == data.email)
    )
    if account is None or not verify_password(data.password, account.password):
        raise invalid_credentials_exception()

    tokens = await create_token_pair(account.id, db)
    await db.commit()

    return tokens


@router.post('/refresh', response_model=TokenSchema, summary='Renovar tokens')
async def refresh_tokens(
    data: RefreshTokenSchema,
    db: AsyncSession = Depends(get_session),
):
    payload, refresh_token = await get_active_refresh_token(
        data.refresh_token, db
    )
    account = await db.get(Account, int(payload['sub']))
    if account is None:
        raise invalid_credentials_exception()

    refresh_token.revoked_at = datetime.now(UTC)
    tokens = await create_token_pair(account.id, db)
    await db.commit()

    return tokens


@router.post(
    '/logout',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Encerrar sessão',
)
async def logout(
    data: RefreshTokenSchema,
    db: AsyncSession = Depends(get_session),
):
    _, refresh_token = await get_active_refresh_token(data.refresh_token, db)
    refresh_token.revoked_at = datetime.now(UTC)
    await db.commit()
