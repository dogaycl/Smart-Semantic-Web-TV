from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.api.deps.db import get_db
from app.schemas.personalization import (
    FavoriteRead,
    UserProfileUpdateRequest,
    WatchHistoryRead,
    WatchHistoryUpsertRequest,
)
from app.schemas.user import UserRead
from app.services.personalization_service import PersonalizationService

router = APIRouter(prefix="/users/me", tags=["users"])
service = PersonalizationService()

ContentIdPath = Annotated[str, Path(min_length=1, max_length=255)]


@router.get("/favorites", response_model=list[FavoriteRead], status_code=status.HTTP_200_OK)
def get_my_favorites(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FavoriteRead]:
    return service.list_favorites(db=db, user=current_user)


@router.post("/favorites/{content_id}", response_model=FavoriteRead, status_code=status.HTTP_200_OK)
def add_to_my_favorites(
    content_id: ContentIdPath,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FavoriteRead:
    return service.add_favorite(db=db, user=current_user, content_id=content_id)


@router.delete("/favorites/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_my_favorites(
    content_id: ContentIdPath,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.remove_favorite(db=db, user=current_user, content_id=content_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/history", response_model=list[WatchHistoryRead], status_code=status.HTTP_200_OK)
def get_my_watch_history(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WatchHistoryRead]:
    return service.list_watch_history(db=db, user=current_user)


@router.post("/history", response_model=WatchHistoryRead, status_code=status.HTTP_200_OK)
def upsert_my_watch_history(
    payload: WatchHistoryUpsertRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchHistoryRead:
    return service.upsert_watch_history(db=db, user=current_user, payload=payload)


@router.patch("/profile", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    return service.update_profile(db=db, user=current_user, payload=payload)
