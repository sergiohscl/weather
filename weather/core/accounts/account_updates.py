from weather.core.accounts.security import hash_password
from weather.models.accounts import Account


def apply_account_updates(
    account: Account,
    name: str | None,
    email: str | None,
    password: str | None,
    avatar_url: str,
    has_new_avatar: bool,
) -> None:
    if name is not None:
        account.name = name
    if email is not None:
        account.email = email
    if password is not None:
        account.password = hash_password(password)
    if has_new_avatar:
        account.avatar = avatar_url
