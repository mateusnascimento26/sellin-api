from dataclasses import dataclass

from domain.ports.user_repository import UserRepository
from domain.value_objects.jwt_token import create_access_token
from domain.value_objects.password import verify_password


@dataclass
class LoginResult:
    success: bool
    token: str | None = None
    error: str | None = None


class Login:
    def __init__(self, user_repository: UserRepository, secret_key: str):
        self.user_repository = user_repository
        self.secret_key = secret_key

    def execute(self, username: str, password: str) -> LoginResult:
        user = self.user_repository.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            return LoginResult(success=False, error="Usuário ou senha inválidos.")

        token = create_access_token(username=user.username, secret_key=self.secret_key)
        return LoginResult(success=True, token=token)