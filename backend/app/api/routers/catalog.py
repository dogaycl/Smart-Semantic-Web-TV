from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user_optional
from app.api.deps.db import get_db
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.catalog import CatalogItemDetailRead, CatalogListResponse
from app.schemas.playback import CatalogPlaybackResponse
from app.services.catalog.service import CatalogService
from app.services.catalog.sync_service import CatalogSyncService
from app.services.playback.service import CatalogPlaybackService
from app.services.playback.sync_service import PlaybackCatalogSyncService

router = APIRouter(prefix="/catalog", tags=["catalog"])
catalog_repository = CatalogRepository()
catalog_service = CatalogService()
sync_service = CatalogSyncService()
playback_sync_service = PlaybackCatalogSyncService(
    catalog_repository=catalog_repository,
    catalog_sync_service=sync_service,
)
playback_service = CatalogPlaybackService(catalog_repository=catalog_repository)

SortOption = Literal["popularity_desc", "rating_desc", "release_date_desc", "title_asc"]
SortParam = Annotated[SortOption, Query()]
LimitParam = Annotated[int, Query(ge=1, le=300)]
OffsetParam = Annotated[int, Query(ge=0)]


def _list_catalog(
    *,
    db: Session,
    content_type: str | None,
    category: str | None,
    genre: str | None,
    search: str | None,
    sort: SortOption,
    limit: int,
    offset: int,
    slugs: str | None,
) -> CatalogListResponse:
    sync_service.ensure_ready(db=db)
    playback_sync_service.ensure_ready(db=db)
    genre_names = catalog_service.filter_genre_names_for_category(category)
    if genre:
        genre_names = list(dict.fromkeys([*(genre_names or []), genre]))
    items = catalog_repository.list_catalog(
        db=db,
        content_type=content_type,
        search=search,
        genre_names=genre_names,
        sort=sort,
        limit=limit,
        offset=offset,
        slugs=[value.strip() for value in slugs.split(",") if value.strip()] if slugs else None,
    )
    total = catalog_repository.count_catalog(
        db=db,
        content_type=content_type,
        search=search,
        genre_names=genre_names,
        slugs=[value.strip() for value in slugs.split(",") if value.strip()] if slugs else None,
    )
    return catalog_service.build_list_response(items=items, total=total, limit=limit, offset=offset)


@router.get("", response_model=CatalogListResponse, status_code=status.HTTP_200_OK)
def list_catalog(
    db: Session = Depends(get_db),
    content_type: str | None = Query(default=None),
    category: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    sort: SortParam = "popularity_desc",
    limit: LimitParam = 48,
    offset: OffsetParam = 0,
    slugs: str | None = Query(default=None),
) -> CatalogListResponse:
    resolved_type = catalog_service.content_type_from_label(content_type) or content_type
    return _list_catalog(
        db=db,
        content_type=resolved_type,
        category=category,
        genre=genre,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
        slugs=slugs,
    )


@router.get("/movies", response_model=CatalogListResponse, status_code=status.HTTP_200_OK)
def list_movies(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    sort: SortParam = "popularity_desc",
    limit: LimitParam = 48,
    offset: OffsetParam = 0,
    slugs: str | None = Query(default=None),
) -> CatalogListResponse:
    return _list_catalog(
        db=db,
        content_type="movie",
        category=category,
        genre=genre,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
        slugs=slugs,
    )


@router.get("/series", response_model=CatalogListResponse, status_code=status.HTTP_200_OK)
def list_series(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    genre: str | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    sort: SortParam = "popularity_desc",
    limit: LimitParam = 48,
    offset: OffsetParam = 0,
    slugs: str | None = Query(default=None),
) -> CatalogListResponse:
    return _list_catalog(
        db=db,
        content_type="tv",
        category=category,
        genre=genre,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
        slugs=slugs,
    )


@router.get("/{slug}", response_model=CatalogItemDetailRead, status_code=status.HTTP_200_OK)
def get_catalog_item(
    slug: str,
    db: Session = Depends(get_db),
) -> CatalogItemDetailRead:
    sync_service.ensure_ready(db=db)
    playback_sync_service.ensure_ready(db=db)
    item = catalog_repository.get_by_slug(db=db, slug=slug)
    if item is None or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found.")
    related_items = catalog_repository.list_related(db=db, item=item)
    return catalog_service.build_detail(item, related_items)


@router.get("/{slug}/playback", response_model=CatalogPlaybackResponse, status_code=status.HTTP_200_OK)
def get_catalog_item_playback(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_optional),
) -> CatalogPlaybackResponse:
    sync_service.ensure_ready(db=db)
    playback_sync_service.ensure_ready(db=db)
    item = catalog_repository.get_by_slug(db=db, slug=slug)
    if item is None or not item.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found.")
    return playback_service.build_response(db=db, item=item, current_user=current_user)
