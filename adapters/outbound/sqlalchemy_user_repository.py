from sqlalchemy.orm import Session

from database import UserModel
from domain.entities.user import User


class SqlAlchemyUserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        model = self.session.query(UserModel).filter_by(username=username).first()
        if model is None:
            return None
        return User(id=model.id, username=model.username, password_hash=model.password_hash, created=model.created)