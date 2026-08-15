from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.catalog import router as catalog_router
from app.api.routers.channels import router as channels_router
from app.api.routers.epg import router as epg_router
from app.api.routers.recommendations import router as recommendations_router
from app.api.routers.search import router as search_router
from app.api.routers.users import router as users_router
from app.api.routers.viewing_plans import router as viewing_plans_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(channels_router)
api_router.include_router(epg_router)
api_router.include_router(search_router)
api_router.include_router(recommendations_router)
api_router.include_router(viewing_plans_router)
api_router.include_router(users_router)
