import re

from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.accounts.security import validate_password
from weather.models.accounts import Account

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


async def validate_email(
    email: str,
    db: AsyncSession,
    excluded_account_id: int | None = None,
) -> tuple[bool, str]:
    """Verifica o formato do e-mail e se ele já pertence a uma conta."""
    if EMAIL_PATTERN.fullmatch(email) is None:
        return False, 'Email inválido.'

    conditions = [Account.email == email]
    if excluded_account_id is not None:
        conditions.append(Account.id != excluded_account_id)

    email_exists = await db.scalar(select(exists().where(*conditions)))
    if email_exists:
        return False, 'Email já está em uso.'

    return True, ''


async def validate_account_data(
    email: str | None,
    password: str | None,
    confirm_password: str | None,
    db: AsyncSession,
    excluded_account_id: int | None = None,
) -> None:
    if password is not None:
        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail='As senhas não correspondem.',
            )
        try:
            validate_password(password)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

    if email is not None:
        email_is_valid, error_message = await validate_email(
            email, db, excluded_account_id
        )
        if not email_is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=error_message,
            )
