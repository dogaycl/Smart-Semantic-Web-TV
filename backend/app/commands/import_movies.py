"""Additively import extra movies from TMDB.

Unlike ``catalog_sync`` (which reconciles the catalog against a fixed set of
genre buckets and deactivates anything outside them), this command only *adds*
movies whose TMDB id is not already stored. It never edits, deactivates, or
removes an existing catalog item.

Usage:
    python -m app.commands.import_movies --limit 800
"""

from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.catalog_item import CatalogItem
from app.services.catalog.providers.tmdb_provider import TMDBProvider
from app.services.catalog.sync_service import CatalogSyncService

logger = logging.getLogger("import_movies")

# Sorts chosen to surface established, watchable films rather than a wall of
# unreleased/low-signal entries. Every /discover call also applies a vote-count
# and rating floor below.
_DISCOVER_SORTS = (
    "popularity.desc",
    "vote_average.desc",
    "revenue.desc",
)
_LIST_ENDPOINTS = ("/movie/popular", "/movie/top_rated")
_MIN_VOTE_COUNT = 120
_MIN_VOTE_AVERAGE = 5.5


def _discover_new_movie_ids(provider: TMDBProvider, existing_ids: set[int], target: int) -> list[int]:
    movie_genres, _ = provider._genre_maps()
    seen: set[int] = set()
    ordered: list[int] = []

    def add(raw_id: object) -> None:
        try:
            tmdb_id = int(raw_id or 0)
        except (TypeError, ValueError):
            return
        if tmdb_id and tmdb_id not in existing_ids and tmdb_id not in seen:
            seen.add(tmdb_id)
            ordered.append(tmdb_id)

    def enough() -> bool:
        return len(ordered) >= target

    # 1. Curated TMDB lists.
    for path in _LIST_ENDPOINTS:
        for page in range(1, 31):
            if enough():
                return ordered
            try:
                payload = provider._request_json(
                    path, params={"language": provider.settings.tmdb_language, "page": page}
                )
            except httpx.HTTPError as exc:
                logger.warning("list %s page %s failed: %s", path, page, exc)
                break
            results = payload.get("results", [])
            if not results:
                break
            for entry in results:
                add(entry.get("id"))

    # 2. Weekly trending.
    for page in range(1, 8):
        if enough():
            return ordered
        try:
            payload = provider._request_json("/trending/movie/week", params={"page": page})
        except httpx.HTTPError as exc:
            logger.warning("trending page %s failed: %s", page, exc)
            break
        for entry in payload.get("results", []):
            if (entry.get("vote_count") or 0) >= 40:
                add(entry.get("id"))

    # 3. Genre sweeps with several sort orders for breadth.
    for genre_name, genre_id in movie_genres.items():
        for sort_by in _DISCOVER_SORTS:
            for page in range(1, 13):
                if enough():
                    return ordered
                params: dict[str, object] = {
                    "language": provider.settings.tmdb_language,
                    "page": page,
                    "sort_by": sort_by,
                    "include_adult": "false",
                    "with_genres": str(genre_id),
                    "vote_count.gte": _MIN_VOTE_COUNT,
                    "vote_average.gte": _MIN_VOTE_AVERAGE,
                }
                try:
                    payload = provider._request_json("/discover/movie", params=params)
                except httpx.HTTPError as exc:
                    logger.warning("discover %s/%s page %s failed: %s", genre_name, sort_by, page, exc)
                    break
                results = payload.get("results", [])
                if not results:
                    break
                for entry in results:
                    add(entry.get("id"))

    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=800, help="Maximum number of new movies to import.")
    parser.add_argument("--report", default="imported_movies.txt", help="Path to write the list of added titles.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    provider = TMDBProvider()
    if not provider.is_configured():
        raise SystemExit("TMDB is not configured (set TMDB_ACCESS_TOKEN or TMDB_API_KEY).")

    db = SessionLocal()
    sync_service = CatalogSyncService(provider=provider)
    started = time.monotonic()
    try:
        existing_ids = set(
            db.scalars(select(CatalogItem.tmdb_id).where(CatalogItem.content_type == "movie")).all()
        )
        logger.info("Existing movies: %d (left untouched).", len(existing_ids))

        new_ids = _discover_new_movie_ids(provider, existing_ids, args.limit)
        logger.info("Discovered %d new candidate movies. Fetching details...", len(new_ids))

        now = datetime.now(timezone.utc)
        added: list[tuple[str, int | None, int]] = []
        for index, tmdb_id in enumerate(new_ids, start=1):
            try:
                payload = provider.fetch_catalog_item(tmdb_id=tmdb_id, content_type="movie")
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("  skip tmdb:%s (%s)", tmdb_id, exc)
                continue
            if not payload.title:
                continue
            sync_service.sync_payload(db=db, payload=payload, synced_at=now, pinned=True)
            added.append((payload.title, payload.release_date.year if payload.release_date else None, tmdb_id))
            if index % 25 == 0:
                db.commit()
                logger.info("  committed %d/%d", index, len(new_ids))
        db.commit()

        added.sort(key=lambda entry: (entry[0] or "").casefold())
        with open(args.report, "w", encoding="utf-8") as handle:
            for title, year, tmdb_id in added:
                handle.write(f"{title} ({year or '-'})  [tmdb:{tmdb_id}]\n")

        elapsed = time.monotonic() - started
        logger.info("")
        logger.info("DONE in %.0fs. Added %d new movies. Report: %s", elapsed, len(added), args.report)
        for title, year, _ in added:
            logger.info("  + %s (%s)", title, year or "-")
    finally:
        db.close()


if __name__ == "__main__":
    main()
