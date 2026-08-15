from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.api.deps.db import get_db
from app.models.user import User
from app.schemas.discovery import RecommendationResponse
from app.services.recommendations.service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendation_service = RecommendationService()


@router.get("", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
def get_recommendations(
    limit: int = Query(default=12, ge=1, le=30),
    window_hours: int | None = Query(default=None, ge=1, le=72),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    return recommendation_service.recommend(
        db=db,
        user=current_user,
        limit=limit,
        window_hours=window_hours,
    )
