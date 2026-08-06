from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

PROJECT_DIRECTORY = Path(__file__).resolve().parents[3]
UPLOADS_DIRECTORY = PROJECT_DIRECTORY / 'uploads'
AVATARS_DIRECTORY = UPLOADS_DIRECTORY / 'avatars'

MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}


async def save_avatar(avatar: UploadFile | None) -> tuple[str, Path | None]:
    if avatar is None:
        return '', None

    extension = ALLOWED_AVATAR_TYPES.get(avatar.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='Envie uma imagem JPEG, PNG ou WebP.',
        )

    content = await avatar.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail='A imagem deve ter no máximo 5 MB.',
        )

    AVATARS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    filename = f'{uuid4()}.{extension}'
    avatar_path = AVATARS_DIRECTORY / filename
    avatar_path.write_bytes(content)

    return f'/uploads/avatars/{filename}', avatar_path


def avatar_path_from_url(avatar_url: str) -> Path | None:
    url_prefix = '/uploads/avatars/'
    if not avatar_url.startswith(url_prefix):
        return None

    filename = avatar_url.removeprefix(url_prefix)
    if Path(filename).name != filename:
        return None

    return AVATARS_DIRECTORY / filename
