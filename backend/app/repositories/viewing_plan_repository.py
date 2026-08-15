from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.viewing_plan import ViewingPlan
from app.models.viewing_plan_item import ViewingPlanItem


PLAN_LOADS = (
    selectinload(ViewingPlan.items),
)


class ViewingPlanRepository:
    def list_for_user(self, *, db: Session, user_id: int, limit: int = 20) -> list[ViewingPlan]:
        statement = (
            select(ViewingPlan)
            .options(*PLAN_LOADS)
            .where(ViewingPlan.user_id == user_id)
            .order_by(ViewingPlan.created_at.desc(), ViewingPlan.id.desc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    def get_for_user(self, *, db: Session, user_id: int, plan_id: int) -> ViewingPlan | None:
        statement = (
            select(ViewingPlan)
            .options(*PLAN_LOADS)
            .where(ViewingPlan.user_id == user_id, ViewingPlan.id == plan_id)
        )
        return db.scalar(statement)

    def create_plan(self, **kwargs) -> ViewingPlan:
        return ViewingPlan(**kwargs)

    def create_item(self, **kwargs) -> ViewingPlanItem:
        return ViewingPlanItem(**kwargs)
