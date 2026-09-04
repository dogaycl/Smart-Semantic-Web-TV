from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserRead


class AuthService:
    def __init__(self) -> None:
        self.user_repository = UserRepository()
        self.user_profile_repository = UserProfileRepository()

    def register_user(self, *, db: Session, payload: RegisterRequest) -> AuthResponse:
        normalized_email = payload.email.lower()

        if self.user_repository.get_by_email(db=db, email=normalized_email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")
        if self.user_repository.get_by_username(db=db, username=payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already taken.")

        user = self.user_repository.create(
            username=payload.username,
            email=normalized_email,
            hashed_password=hash_password(payload.password),
        )
        db.add(user)

        try:
            db.flush()
            profile = self.user_profile_repository.create(
                user_id=user.id,
                display_name=payload.display_name or payload.username,
                avatar_url=payload.avatar_url,
                interests=payload.interests,
                preferred_categories=payload.preferred_categories,
            )
            db.add(profile)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User registration conflicts with existing data.",
            ) from exc

        persisted_user = self.user_repository.get_by_id(db=db, user_id=user.id)
        if persisted_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registered user could not be reloaded.",
            )

        return self._build_auth_response(persisted_user)

    def authenticate_user(self, *, db: Session, payload: LoginRequest) -> AuthResponse:
        user = self.user_repository.get_by_email(db=db, email=payload.email.lower())
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return self._build_auth_response(user)

    def _build_auth_response(self, user) -> AuthResponse:
        return AuthResponse(
            access_token=create_access_token(subject=user.id),
            user=UserRead.model_validate(user),
        )
