from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.favorite_repository import FavoriteRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.user_repository import UserRepository
from app.repositories.watch_history_repository import WatchHistoryRepository
from app.schemas.personalization import (
    FavoriteRead,
    UserProfileUpdateRequest,
    WatchHistoryRead,
    WatchHistoryUpsertRequest,
)
from app.schemas.user import UserRead


class PersonalizationService:
    def __init__(self) -> None:
        self.favorite_repository = FavoriteRepository()
        self.watch_history_repository = WatchHistoryRepository()
        self.user_repository = UserRepository()
        self.user_profile_repository = UserProfileRepository()

    def list_favorites(self, *, db: Session, user: User) -> list[FavoriteRead]:
        favorites = self.favorite_repository.list_for_user(db=db, user_id=user.id)
        return [FavoriteRead.model_validate(favorite) for favorite in favorites]

    def add_favorite(self, *, db: Session, user: User, content_id: str) -> FavoriteRead:
        favorite = self.favorite_repository.get_for_user_and_content(
            db=db,
            user_id=user.id,
            content_id=content_id,
        )
        if favorite is None:
            favorite = self.favorite_repository.create(user_id=user.id, content_id=content_id)
            db.add(favorite)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Favorite conflicts with existing data.",
                ) from exc
            db.refresh(favorite)

        return FavoriteRead.model_validate(favorite)

    def remove_favorite(self, *, db: Session, user: User, content_id: str) -> None:
        favorite = self.favorite_repository.get_for_user_and_content(
            db=db,
            user_id=user.id,
            content_id=content_id,
        )
        if favorite is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found.")

        self.favorite_repository.delete(db=db, favorite=favorite)
        db.commit()

    def list_watch_history(self, *, db: Session, user: User) -> list[WatchHistoryRead]:
        entries = self.watch_history_repository.list_for_user(db=db, user_id=user.id)
        return [WatchHistoryRead.model_validate(entry) for entry in entries]

    def upsert_watch_history(
        self,
        *,
        db: Session,
        user: User,
        payload: WatchHistoryUpsertRequest,
    ) -> WatchHistoryRead:
        entry = self.watch_history_repository.get_for_user_content(
            db=db,
            user_id=user.id,
            content_id=payload.content_id,
            content_type=payload.content_type,
        )
        last_watched_at = payload.last_watched_at or datetime.now(timezone.utc)

        if entry is None:
            entry = self.watch_history_repository.create(
                user_id=user.id,
                content_id=payload.content_id,
                content_type=payload.content_type,
                watch_position_seconds=payload.watch_position_seconds,
                total_watched_duration_seconds=payload.total_watched_duration_seconds,
                is_completed=payload.is_completed,
                last_watched_at=last_watched_at,
            )
            db.add(entry)
        else:
            entry.watch_position_seconds = payload.watch_position_seconds
            entry.total_watched_duration_seconds = payload.total_watched_duration_seconds
            entry.is_completed = payload.is_completed
            entry.last_watched_at = last_watched_at

        db.commit()
        db.refresh(entry)
        return WatchHistoryRead.model_validate(entry)

    def update_profile(
        self,
        *,
        db: Session,
        user: User,
        payload: UserProfileUpdateRequest,
    ) -> UserRead:
        if user.profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found.",
            )

        profile = self.user_profile_repository.update(
            profile=user.profile,
            display_name=payload.display_name,
            avatar_url=str(payload.avatar_url) if payload.avatar_url else None,
            interests=payload.interests,
            preferred_categories=payload.preferred_categories,
        )
        db.add(profile)
        db.commit()

        refreshed_user = self.user_repository.get_by_id(db=db, user_id=user.id)
        if refreshed_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Updated user could not be reloaded.",
            )

        return UserRead.model_validate(refreshed_user)
