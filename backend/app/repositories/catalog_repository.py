from datetime import datetime

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.models.playback_source import PlaybackSource


CATALOG_EAGER_LOADS = (
    selectinload(CatalogItem.genres),
    selectinload(CatalogItem.seasons),
    selectinload(CatalogItem.videos),
    selectinload(CatalogItem.playback_sources),
)


class CatalogRepository:
    def count_active(self, *, db: Session) -> int:
        statement = select(func.count(CatalogItem.id)).where(CatalogItem.is_active.is_(True))
        return int(db.scalar(statement) or 0)

    def latest_sync_at(self, *, db: Session) -> datetime | None:
        statement = select(func.max(CatalogItem.last_synced_at)).where(CatalogItem.is_active.is_(True))
        return db.scalar(statement)

    def list_catalog(
        self,
        *,
        db: Session,
        content_type: str | None = None,
        search: str | None = None,
        genre_names: list[str] | None = None,
        sort: str = "popularity_desc",
        limit: int = 48,
        offset: int = 0,
        slugs: list[str] | None = None,
    ) -> list[CatalogItem]:
        statement = self._base_statement(
            content_type=content_type,
            search=search,
            genre_names=genre_names,
            slugs=slugs,
        )
        statement = statement.options(*CATALOG_EAGER_LOADS).order_by(*self._sort_clauses(sort)).limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def count_catalog(
        self,
        *,
        db: Session,
        content_type: str | None = None,
        search: str | None = None,
        genre_names: list[str] | None = None,
        slugs: list[str] | None = None,
    ) -> int:
        statement = self._base_statement(
            content_type=content_type,
            search=search,
            genre_names=genre_names,
            slugs=slugs,
        )
        count_statement = select(func.count()).select_from(statement.subquery())
        return int(db.scalar(count_statement) or 0)

    def get_by_slug(self, *, db: Session, slug: str) -> CatalogItem | None:
        statement = (
            select(CatalogItem)
            .options(*CATALOG_EAGER_LOADS)
            .where(CatalogItem.slug == slug)
        )
        return db.scalar(statement)

    def get_by_tmdb(self, *, db: Session, content_type: str, tmdb_id: int) -> CatalogItem | None:
        statement = (
            select(CatalogItem)
            .options(*CATALOG_EAGER_LOADS)
            .where(
                CatalogItem.content_type == content_type,
                CatalogItem.tmdb_id == tmdb_id,
            )
        )
        return db.scalar(statement)

    def list_related(self, *, db: Session, item: CatalogItem, limit: int = 4) -> list[CatalogItem]:
        genre_names = [genre.name for genre in item.genres]
        related: list[CatalogItem] = []

        if genre_names:
            related_ids = (
                select(CatalogItem.id)
                .join(CatalogItem.genres)
                .where(CatalogItem.is_active.is_(True))
                .where(CatalogItem.id != item.id)
                .where(CatalogItem.content_type == item.content_type)
                .where(CatalogGenre.name.in_(genre_names))
                .distinct()
                .subquery()
            )
            statement = (
                select(CatalogItem)
                .options(*CATALOG_EAGER_LOADS)
                .where(CatalogItem.id.in_(select(related_ids.c.id)))
                .order_by(CatalogItem.vote_average.desc(), CatalogItem.popularity.desc(), CatalogItem.title.asc())
                .limit(limit)
            )
            related = list(db.scalars(statement).all())

        if len(related) >= limit:
            return related[:limit]

        existing_ids = {entry.id for entry in related}
        existing_ids.add(item.id)
        fallback_statement = (
            select(CatalogItem)
            .options(*CATALOG_EAGER_LOADS)
            .where(CatalogItem.is_active.is_(True))
            .where(CatalogItem.content_type == item.content_type)
            .where(CatalogItem.id.not_in(existing_ids))
            .order_by(CatalogItem.vote_average.desc(), CatalogItem.popularity.desc(), CatalogItem.title.asc())
            .limit(limit - len(related))
        )
        related.extend(list(db.scalars(fallback_statement).all()))
        return related[:limit]

    def list_active(self, *, db: Session) -> list[CatalogItem]:
        statement = (
            select(CatalogItem)
            .options(*CATALOG_EAGER_LOADS)
            .where(CatalogItem.is_active.is_(True))
            .order_by(CatalogItem.title.asc())
        )
        return list(db.scalars(statement).all())

    def find_by_title_and_year(
        self,
        *,
        db: Session,
        title_variants: list[str],
        release_year: int | None,
        content_type: str,
    ) -> CatalogItem | None:
        normalized = [value.strip().lower() for value in title_variants if value.strip()]
        if not normalized:
            return None

        statement = (
            select(CatalogItem)
            .options(*CATALOG_EAGER_LOADS)
            .where(CatalogItem.is_active.is_(True))
            .where(CatalogItem.content_type == content_type)
            .where(
                or_(
                    func.lower(CatalogItem.title).in_(normalized),
                    func.lower(CatalogItem.original_title).in_(normalized),
                )
            )
            .order_by(CatalogItem.release_date.desc(), CatalogItem.id.desc())
        )
        candidates = list(db.scalars(statement).all())
        if release_year is None:
            return candidates[0] if candidates else None

        for item in candidates:
            if item.release_date and item.release_date.year == release_year:
                return item
        return candidates[0] if candidates else None

    def create(self, **kwargs) -> CatalogItem:
        return CatalogItem(**kwargs)

    def _base_statement(
        self,
        *,
        content_type: str | None,
        search: str | None,
        genre_names: list[str] | None,
        slugs: list[str] | None,
    ) -> Select[tuple[CatalogItem]]:
        statement: Select[tuple[CatalogItem]] = select(CatalogItem).where(CatalogItem.is_active.is_(True))

        if content_type:
            statement = statement.where(CatalogItem.content_type == content_type)

        if slugs:
            statement = statement.where(CatalogItem.slug.in_(slugs))

        if search:
            search_value = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    CatalogItem.title.ilike(search_value),
                    CatalogItem.original_title.ilike(search_value),
                )
            )

        if genre_names:
            matching_ids = (
                select(CatalogGenre.content_item_id)
                .where(CatalogGenre.name.in_(genre_names))
                .distinct()
            )
            statement = statement.where(CatalogItem.id.in_(matching_ids))

        return statement

    def _sort_clauses(self, sort: str):
        if sort == "title_asc":
            return (CatalogItem.title.asc(),)
        if sort == "rating_desc":
            return (CatalogItem.vote_average.desc(), CatalogItem.popularity.desc(), CatalogItem.title.asc())
        if sort == "release_date_desc":
            return (CatalogItem.release_date.desc(), CatalogItem.popularity.desc(), CatalogItem.title.asc())
        if sort == "playable_desc":
            # Titles with a real, working playback source lead the list; everything else keeps
            # the default popularity ordering behind them.
            playable_ids = (
                select(PlaybackSource.content_item_id)
                .where(PlaybackSource.is_active.is_(True), PlaybackSource.last_error.is_(None))
                .distinct()
            )
            playable_rank = case((CatalogItem.id.in_(playable_ids), 0), else_=1)
            return (
                playable_rank.asc(),
                CatalogItem.popularity.desc(),
                CatalogItem.vote_average.desc(),
                CatalogItem.title.asc(),
            )
        return (CatalogItem.popularity.desc(), CatalogItem.vote_average.desc(), CatalogItem.title.asc())
