from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.api.deps.db import get_db
from app.api.routers import viewing_plans as viewing_plans_router
from app.models.user import User
from app.schemas.planner import ViewingPlanGenerateRequest, ViewingPlanListResponse, ViewingPlanRead

router = APIRouter(prefix="/my-channel", tags=["my-channel"])


@router.post("/generate", response_model=ViewingPlanRead, status_code=status.HTTP_201_CREATED)
def generate_my_channel(
    payload: ViewingPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ViewingPlanRead:
    return viewing_plans_router.viewing_planner_service.generate_plan(db=db, user=current_user, payload=payload)


@router.get("", response_model=ViewingPlanListResponse, status_code=status.HTTP_200_OK)
def list_my_channel_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ViewingPlanListResponse:
    return viewing_plans_router.viewing_planner_service.list_plans(db=db, user=current_user)


@router.get("/{plan_id}", response_model=ViewingPlanRead, status_code=status.HTTP_200_OK)
def get_my_channel_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ViewingPlanRead:
    return viewing_plans_router.viewing_planner_service.get_plan(db=db, user=current_user, plan_id=plan_id)
