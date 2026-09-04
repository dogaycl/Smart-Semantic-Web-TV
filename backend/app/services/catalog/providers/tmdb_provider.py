from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# TMDB itself is reliable, but the network path to api.themoviedb.org regularly drops a
# connection mid-handshake (observed WinError 10054 / RemoteProtocolError on ~10-20% of a
# long sequential sync). Without this retry a single transient drop aborts the whole
# catalog sync and nothing is committed.
MAX_ATTEMPTS = 4
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
BASE_RETRY_DELAY_SECONDS = 1.0
MAX_RETRY_DELAY_SECONDS = 8.0
from app.services.catalog.curation import CATALOG_BUCKETS
from app.services.catalog.providers.base import (
    CatalogCandidate,
    CatalogProvider,
    CatalogSeasonPayload,
    CatalogVideoPayload,
    ContentType,
    ExternalCatalogItemPayload,
)


class TMDBProvider(CatalogProvider):
    base_api_url = "https://api.themoviedb.org/3"
    default_image_base_url = "https://image.tmdb.org/t/p/"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._configuration_cache: dict[str, Any] | None = None
        self._movie_genres: dict[str, int] | None = None
        self._tv_genres: dict[str, int] | None = None

    def is_configured(self) -> bool:
        return bool(self.settings.tmdb_access_token or self.settings.tmdb_api_key)

    def discover_catalog_candidates(self, *, target_items: int) -> list[CatalogCandidate]:
        if not self.is_configured():
            return []

        candidates: list[CatalogCandidate] = []
        seen: set[tuple[str, int]] = set()
        movie_genres, tv_genres = self._genre_maps()

        for bucket in CATALOG_BUCKETS:
            genre_map = movie_genres if bucket.content_type == "movie" else tv_genres
            genre_ids = [genre_map[name] for name in bucket.genre_names if name in genre_map]
            if bucket.genre_names and not genre_ids:
                continue

            for page in range(1, bucket.pages + 1):
                params: dict[str, Any] = {
                    "language": self.settings.tmdb_language,
                    "page": page,
                    "sort_by": bucket.sort_by,
                    "include_adult": "false",
                    "vote_count.gte": bucket.min_vote_count,
                    "vote_average.gte": bucket.min_vote_average,
                }
                if bucket.content_type == "movie":
                    params["include_video"] = "false"
                if genre_ids:
                    params["with_genres"] = "|".join(str(genre_id) for genre_id in genre_ids)

                payload = self._request_json(f"/discover/{bucket.content_type}", params=params)
                for item in payload.get("results", []):
                    tmdb_id = int(item.get("id") or 0)
                    title = item.get("title") or item.get("name") or ""
                    if not tmdb_id or not title:
                        continue

                    key = (bucket.content_type, tmdb_id)
                    if key in seen:
                        continue

                    seen.add(key)
                    candidates.append(
                        CatalogCandidate(
                            tmdb_id=tmdb_id,
                            content_type=bucket.content_type,
                            title=title,
                        )
                    )
                    if len(candidates) >= target_items:
                        return candidates

        return candidates

    def fetch_catalog_item(self, *, tmdb_id: int, content_type: ContentType) -> ExternalCatalogItemPayload:
        if content_type == "movie":
            return self._fetch_movie(tmdb_id)
        return self._fetch_tv(tmdb_id)

    def search_catalog_item(
        self,
        *,
        title: str,
        content_type: ContentType,
        release_year: int | None = None,
    ) -> CatalogCandidate | None:
        if not self.is_configured():
            return None

        params: dict[str, Any] = {
            "language": self.settings.tmdb_language,
            "query": title,
            "include_adult": "false",
            "page": 1,
        }
        if release_year:
            if content_type == "movie":
                params["primary_release_year"] = release_year
            else:
                params["first_air_date_year"] = release_year

        payload = self._request_json(f"/search/{content_type}", params=params)
        results = payload.get("results", [])
        if not results:
            return None

        normalized_query = self._normalize_title(title)
        for value in results:
            tmdb_id = self._safe_int(value.get("id"))
            candidate_title = value.get("title") or value.get("name") or ""
            if not tmdb_id or not candidate_title:
                continue

            if release_year:
                release_value = value.get("release_date") or value.get("first_air_date")
                parsed_release = self._parse_date(release_value)
                if parsed_release and parsed_release.year != release_year:
                    continue

            if self._normalize_title(candidate_title) != normalized_query:
                continue

            return CatalogCandidate(
                tmdb_id=tmdb_id,
                content_type=content_type,
                title=candidate_title,
            )

        first = results[0]
        tmdb_id = self._safe_int(first.get("id"))
        candidate_title = first.get("title") or first.get("name") or ""
        if not tmdb_id or not candidate_title:
            return None
        return CatalogCandidate(tmdb_id=tmdb_id, content_type=content_type, title=candidate_title)

    def _fetch_movie(self, tmdb_id: int) -> ExternalCatalogItemPayload:
        payload = self._request_json(
            f"/movie/{tmdb_id}",
            params={
                "language": self.settings.tmdb_language,
                "append_to_response": "videos,credits",
            },
        )
        videos = self._map_videos(payload.get("videos", {}).get("results", []))
        credits = payload.get("credits", {})
        return ExternalCatalogItemPayload(
            tmdb_id=tmdb_id,
            content_type="movie",
            title=payload.get("title") or "",
            original_title=payload.get("original_title"),
            overview=payload.get("overview"),
            genres=self._map_genres(payload.get("genres", [])),
            release_date=self._parse_date(payload.get("release_date")),
            runtime_minutes=self._safe_int(payload.get("runtime")),
            poster_url=self._image_url(payload.get("poster_path"), kind="poster"),
            backdrop_url=self._image_url(payload.get("backdrop_path"), kind="backdrop"),
            vote_average=self._safe_float(payload.get("vote_average")),
            popularity=self._safe_float(payload.get("popularity")),
            original_language=payload.get("original_language"),
            status=payload.get("status"),
            top_cast=self._map_cast(credits.get("cast", [])),
            top_crew=self._map_movie_crew(credits.get("crew", [])),
            tmdb_url=self._tmdb_url("movie", tmdb_id),
            videos=videos,
        )

    def _fetch_tv(self, tmdb_id: int) -> ExternalCatalogItemPayload:
        payload = self._request_json(
            f"/tv/{tmdb_id}",
            params={
                "language": self.settings.tmdb_language,
                "append_to_response": "videos,aggregate_credits",
            },
        )
        videos = self._map_videos(payload.get("videos", {}).get("results", []))
        aggregate_credits = payload.get("aggregate_credits", {})
        return ExternalCatalogItemPayload(
            tmdb_id=tmdb_id,
            content_type="tv",
            title=payload.get("name") or "",
            original_title=payload.get("original_name"),
            overview=payload.get("overview"),
            genres=self._map_genres(payload.get("genres", [])),
            release_date=self._parse_date(payload.get("first_air_date")),
            runtime_minutes=self._first_runtime(payload.get("episode_run_time", [])),
            poster_url=self._image_url(payload.get("poster_path"), kind="poster"),
            backdrop_url=self._image_url(payload.get("backdrop_path"), kind="backdrop"),
            vote_average=self._safe_float(payload.get("vote_average")),
            popularity=self._safe_float(payload.get("popularity")),
            original_language=payload.get("original_language"),
            status=payload.get("status"),
            top_cast=self._map_cast(aggregate_credits.get("cast", [])),
            top_crew=self._map_tv_crew(payload.get("created_by", []), aggregate_credits.get("crew", [])),
            number_of_seasons=self._safe_int(payload.get("number_of_seasons")),
            number_of_episodes=self._safe_int(payload.get("number_of_episodes")),
            tmdb_url=self._tmdb_url("tv", tmdb_id),
            seasons=self._map_seasons(payload.get("seasons", [])),
            videos=videos,
        )

    def _request_json(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_params = dict(params or {})
        headers = {
            "accept": "application/json",
        }
        if self.settings.tmdb_access_token:
            headers["Authorization"] = f"Bearer {self.settings.tmdb_access_token}"
        elif self.settings.tmdb_api_key:
            request_params["api_key"] = self.settings.tmdb_api_key

        last_exc: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = httpx.get(
                    f"{self.base_api_url}{path}",
                    params=request_params,
                    headers=headers,
                    timeout=self.settings.catalog_request_timeout_seconds,
                )
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt == MAX_ATTEMPTS:
                    raise
                logger.warning(
                    "TMDB request %s failed (attempt %s/%s), retrying: %s",
                    path, attempt, MAX_ATTEMPTS, exc,
                )
                time.sleep(self._retry_delay(attempt=attempt, response=None))
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_ATTEMPTS:
                logger.warning(
                    "TMDB request %s got HTTP %s (attempt %s/%s), retrying.",
                    path, response.status_code, attempt, MAX_ATTEMPTS,
                )
                time.sleep(self._retry_delay(attempt=attempt, response=response))
                continue

            response.raise_for_status()
            return response.json()

        raise last_exc or RuntimeError(f"TMDB request {path} failed after retries.")

    @staticmethod
    def _retry_delay(*, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            header_value = response.headers.get("retry-after")
            if header_value:
                try:
                    return min(float(header_value), MAX_RETRY_DELAY_SECONDS)
                except ValueError:
                    pass
        return min(BASE_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)

    def _genre_maps(self) -> tuple[dict[str, int], dict[str, int]]:
        if self._movie_genres is None:
            payload = self._request_json("/genre/movie/list", params={"language": "en"})
            self._movie_genres = {entry["name"]: int(entry["id"]) for entry in payload.get("genres", [])}
        if self._tv_genres is None:
            payload = self._request_json("/genre/tv/list", params={"language": "en"})
            self._tv_genres = {entry["name"]: int(entry["id"]) for entry in payload.get("genres", [])}
        return self._movie_genres, self._tv_genres

    def _configuration(self) -> dict[str, Any]:
        if self._configuration_cache is None:
            try:
                self._configuration_cache = self._request_json("/configuration")
            except httpx.HTTPError:
                self._configuration_cache = {
                    "images": {
                        "secure_base_url": self.default_image_base_url,
                        "poster_sizes": ["w500"],
                        "backdrop_sizes": ["original"],
                    }
                }
        return self._configuration_cache

    def _image_url(self, file_path: str | None, *, kind: str) -> str | None:
        if not file_path:
            return None

        images = self._configuration().get("images", {})
        base_url = images.get("secure_base_url") or self.default_image_base_url
        if kind == "poster":
            size = "w500"
        else:
            size = "original"
        return f"{base_url}{size}{file_path}"

    def _map_genres(self, values: list[dict[str, Any]]) -> list[tuple[int, str]]:
        mapped: list[tuple[int, str]] = []
        for value in values:
            genre_id = self._safe_int(value.get("id"))
            name = value.get("name")
            if genre_id is None or not name:
                continue
            mapped.append((genre_id, name))
        return mapped

    def _map_seasons(self, values: list[dict[str, Any]]) -> list[CatalogSeasonPayload]:
        seasons: list[CatalogSeasonPayload] = []
        for value in values:
            season_number = self._safe_int(value.get("season_number"))
            if season_number is None:
                continue
            seasons.append(
                CatalogSeasonPayload(
                    tmdb_season_id=self._safe_int(value.get("id")),
                    season_number=season_number,
                    name=value.get("name") or f"Season {season_number}",
                    overview=value.get("overview"),
                    air_date=self._parse_date(value.get("air_date")),
                    episode_count=self._safe_int(value.get("episode_count")),
                    poster_url=self._image_url(value.get("poster_path"), kind="poster"),
                )
            )
        return seasons

    def _map_videos(self, values: list[dict[str, Any]]) -> list[CatalogVideoPayload]:
        videos: list[CatalogVideoPayload] = []
        for value in values:
            video_id = value.get("id")
            key = value.get("key")
            site = value.get("site")
            video_type = value.get("type")
            name = value.get("name")
            if not video_id or not key or not site or not video_type or not name:
                continue
            videos.append(
                CatalogVideoPayload(
                    tmdb_video_id=str(video_id),
                    name=name,
                    site=site,
                    type=video_type,
                    video_key=key,
                    official=bool(value.get("official")),
                    language=value.get("iso_639_1"),
                    country=value.get("iso_3166_1"),
                    published_at=self._parse_datetime(value.get("published_at")),
                )
            )
        videos.sort(
            key=lambda item: (
                item.site != "YouTube",
                item.type != "Trailer",
                not item.official,
                item.name.lower(),
            )
        )
        return videos

    def _map_cast(self, values: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for value in values:
            name = value.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
            if len(names) >= 8:
                break
        return names

    def _map_movie_crew(self, values: list[dict[str, Any]]) -> list[str]:
        # Keep the person's role in the string ("Denis Villeneuve (Director)") so the assistant
        # can answer "who directed this" instead of only seeing an unlabelled list of names.
        priority_jobs = ("Director", "Writer", "Screenplay", "Story", "Producer")
        entries: list[str] = []
        seen: set[str] = set()
        for job in priority_jobs:
            for value in values:
                if value.get("job") != job:
                    continue
                name = value.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                entries.append(f"{name} ({job})")
                if len(entries) >= 6:
                    return entries
        return entries

    def _map_tv_crew(self, created_by: list[dict[str, Any]], aggregate_crew: list[dict[str, Any]]) -> list[str]:
        entries: list[str] = []
        seen: set[str] = set()
        for value in created_by:
            name = value.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            entries.append(f"{name} (Creator)")
        for value in aggregate_crew:
            name = value.get("name")
            if not name or name in seen:
                continue
            role = next(
                (job.get("job") for job in value.get("jobs", []) if job.get("job") in {"Director", "Writer", "Executive Producer"}),
                None,
            )
            if role is None:
                continue
            seen.add(name)
            entries.append(f"{name} ({role})")
            if len(entries) >= 6:
                break
        return entries

    def _first_runtime(self, values: list[Any]) -> int | None:
        for value in values:
            runtime = self._safe_int(value)
            if runtime:
                return runtime
        return None

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _normalize_title(self, value: str) -> str:
        return " ".join(value.casefold().replace(":", " ").replace("-", " ").split())

    def _safe_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _tmdb_url(self, content_type: ContentType, tmdb_id: int) -> str:
        return f"https://www.themoviedb.org/{content_type}/{tmdb_id}"
