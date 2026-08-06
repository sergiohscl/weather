from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from weather.core.accounts.account_updates import apply_account_updates
from weather.core.accounts.security import hash_password
from weather.core.accounts.storage import avatar_path_from_url, save_avatar
from weather.core.accounts.validators import validate_account_data
from weather.core.database import get_session
from weather.models.accounts import Account
from weather.schemas.accounts import (
    AccountListPublicSchema,
    AccountPublicSchema,
)

router = APIRouter()


@router.post(
    path='/',
    status_code=status.HTTP_201_CREATED,
    summary='Criar nova conta',
    response_model=AccountPublicSchema,
)
async def create_account(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    avatar: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_session),
):
    await validate_account_data(email, password, confirm_password, db)

    avatar_url, avatar_path = await save_avatar(avatar)

    db_account = Account(
        name=name,
        email=email,
        password=hash_password(password),
        avatar=avatar_url,
    )

    db.add(db_account)
    try:
        await db.commit()
        await db.refresh(db_account)
    except Exception:
        await db.rollback()
        if avatar_path is not None:
            avatar_path.unlink(missing_ok=True)
        raise

    return db_account


@router.get(
    path='/',
    status_code=status.HTTP_200_OK,
    response_model=AccountListPublicSchema,
    summary='Listar contas',
)
async def list_accounts(
    db: AsyncSession = Depends(get_session),
):
    result = await db.scalars(select(Account))
    accounts = result.all()

    return {
        'accounts': accounts,
    }


@router.get(
    path='/{account_id}',
    status_code=status.HTTP_200_OK,
    response_model=AccountPublicSchema,
    summary='Buscar conta por ID',
)
async def ger_accounts(
    account_id: int,
    db: AsyncSession = Depends(get_session),
):
    account = await db.get(Account, account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Conta não encontrada',
        )

    return account


@router.put(
    path='/{account_id}',
    status_code=status.HTTP_200_OK,
    response_model=AccountPublicSchema,
    summary='Atualizar conta',
)
async def update_account(
    account_id: int,
    name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    password: str | None = Form(default=None),
    confirm_password: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_session),
):
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Conta não encontrada',
        )

    await validate_account_data(
        email,
        password,
        confirm_password,
        db,
        excluded_account_id=account_id,
    )

    avatar_url, new_avatar_path = await save_avatar(avatar)
    old_avatar_path = avatar_path_from_url(account.avatar)

    apply_account_updates(
        account, name, email, password, avatar_url, avatar is not None
    )

    try:
        await db.commit()
        await db.refresh(account)
    except Exception:
        await db.rollback()
        if new_avatar_path is not None:
            new_avatar_path.unlink(missing_ok=True)
        raise

    if avatar is not None and old_avatar_path is not None:
        old_avatar_path.unlink(missing_ok=True)

    return account


@router.delete(
    path='/{account_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Deletar conta',
)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_session),
):
    account = await db.get(Account, account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Conta não encontrada',
        )

    avatar_path = avatar_path_from_url(account.avatar)
    await db.delete(account)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    if avatar_path is not None:
        avatar_path.unlink(missing_ok=True)
