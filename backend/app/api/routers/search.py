from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user_optional
from app.api.deps.db import get_db
from app.models.user import User
from app.schemas.discovery import SemanticSearchRequest, SemanticSearchResponse
from app.services.search.service import SemanticSearchService

router = APIRouter(prefix="/search", tags=["search"])
search_service = SemanticSearchService()


@router.post("/semantic", response_model=SemanticSearchResponse, status_code=status.HTTP_200_OK)
def semantic_search(
    payload: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> SemanticSearchResponse:
    return search_service.search(
        db=db,
        user=current_user,
        query=payload.query,
        limit=payload.limit,
        window_hours=payload.window_hours,
    )
