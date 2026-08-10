from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User


class UserRepository:
    def get_by_id(self, *, db: Session, user_id: int) -> User | None:
        statement = select(User).options(joinedload(User.profile)).where(User.id == user_id)
        return db.scalar(statement)

    def get_by_email(self, *, db: Session, email: str) -> User | None:
        statement = select(User).options(joinedload(User.profile)).where(User.email == email)
        return db.scalar(statement)

    def get_by_username(self, *, db: Session, username: str) -> User | None:
        statement = select(User).options(joinedload(User.profile)).where(User.username == username)
        return db.scalar(statement)

    def create(
        self,
        *,
        username: str,
        email: str,
        hashed_password: str,
        role: str = "user",
    ) -> User:
        return User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )
