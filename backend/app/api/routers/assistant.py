from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.api.deps.db import get_db
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.assistant.service import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])
assistant_service = AssistantService()


@router.post("/chat", response_model=AssistantChatResponse, status_code=status.HTTP_200_OK)
def assistant_chat(
    payload: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantChatResponse:
    return assistant_service.chat(db=db, user=current_user, payload=payload)
