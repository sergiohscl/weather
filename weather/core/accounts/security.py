from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

MIN_PASSWORD_LENGTH = 6
SEQUENCE_LENGTH = 3


def validate_password(password: str) -> None:
    """Valida as regras de negócio da senha antes de armazená-la."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError('A senha deve conter pelo menos 6 caracteres.')

    normalized_password = password.lower()
    for start in range(len(normalized_password) - SEQUENCE_LENGTH + 1):
        sequence = normalized_password[start: start + SEQUENCE_LENGTH]
        if _is_consecutive_sequence(sequence):
            raise ValueError(
                'A senha não pode conter sequências como 123, abc ou cba.'
            )


def _is_consecutive_sequence(value: str) -> bool:
    """Identifica sequências alfanuméricas consecutivas, em ambos sentidos."""
    if not value.isascii() or not value.isalnum():
        return False

    characters = zip(value, value[1:])
    differences = [
        ord(next_char) - ord(char) for char, next_char in characters
    ]
    return all(difference == 1 for difference in differences) or all(
        difference == -1 for difference in differences
    )


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)
