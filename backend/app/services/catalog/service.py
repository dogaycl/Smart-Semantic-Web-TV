from datetime import datetime

from app.models.catalog_item import CatalogItem
from app.models.catalog_video import CatalogVideo


TMDB_ATTRIBUTION = {
    "source": "TMDB",
    "notice": "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    "url": "https://www.themoviedb.org",
    "logo_url": "https://www.themoviedb.org/assets/2/v4/logos/v2/blue_long_2-9665a76b1ae401a510ec1e0ca40ddcb3b0cfe45f1d51b77a308fea0845885648.svg",
}


class CatalogService:
    def build_list_response(
        self,
        *,
        items: list[CatalogItem],
        total: int,
        limit: int,
        offset: int,
    ) -> dict:
        return {
            "items": [self.build_summary(item) for item in items],
            "total": total,
            "limit": limit,
            "offset": offset,
            "attribution": TMDB_ATTRIBUTION,
        }

    def build_detail(self, item: CatalogItem, related_items: list[CatalogItem]) -> dict:
        trailer = self._preferred_video(item.videos)
        return {
            **self.build_summary(item),
            "top_cast": item.top_cast or [],
            "top_crew": item.top_crew or [],
            "videos": [self.build_video(video) for video in item.videos],
            "seasons": [
                {
                    "season_number": season.season_number,
                    "name": season.name,
                    "overview": season.overview,
                    "air_date": season.air_date,
                    "episode_count": season.episode_count,
                    "poster_url": season.poster_url,
                }
                for season in item.seasons
            ],
            "trailer": self.build_video(trailer) if trailer else None,
            "related_items": [self.build_summary(related) for related in related_items],
            "attribution": TMDB_ATTRIBUTION,
        }

    def build_summary(self, item: CatalogItem) -> dict:
        genres = [genre.name for genre in item.genres]
        trailer = self._preferred_video(item.videos)
        release_date = item.release_date.isoformat() if item.release_date else None
        return {
            "id": item.id,
            "slug": item.slug,
            "content_type": item.content_type,
            "tmdb_id": item.tmdb_id,
            "title": item.title,
            "original_title": item.original_title,
            "overview": item.overview,
            "genres": genres,
            "release_date": release_date,
            "year": item.release_date.year if item.release_date else None,
            "runtime_minutes": item.runtime_minutes,
            "runtime_display": self.runtime_display(item),
            "poster_url": item.poster_url,
            "backdrop_url": item.backdrop_url,
            "rating": round(item.vote_average, 1) if item.vote_average is not None else None,
            "popularity": round(item.popularity, 1) if item.popularity is not None else None,
            "language": item.original_language,
            "status": item.status,
            "number_of_seasons": item.number_of_seasons,
            "number_of_episodes": item.number_of_episodes,
            "category_label": "Movies" if item.content_type == "movie" else "Series",
            "primary_genre": genres[0] if genres else ("Movie" if item.content_type == "movie" else "TV Series"),
            "tmdb_url": item.tmdb_url,
            "has_trailer": trailer is not None,
            "last_synced_at": item.last_synced_at.isoformat() if isinstance(item.last_synced_at, datetime) else None,
        }

    def build_video(self, video: CatalogVideo | None) -> dict | None:
        if video is None:
            return None
        return {
            "name": video.name,
            "site": video.site,
            "type": video.type,
            "official": video.official,
            "published_at": video.published_at.isoformat() if video.published_at else None,
            "embed_url": self.video_embed_url(video.site, video.video_key),
        }

    def runtime_display(self, item: CatalogItem) -> str:
        if item.content_type == "tv":
            if item.number_of_seasons:
                label = "season" if item.number_of_seasons == 1 else "seasons"
                return f"{item.number_of_seasons} {label}"
            if item.runtime_minutes:
                return f"{item.runtime_minutes}m / ep"
            return "Series"

        if not item.runtime_minutes:
            return "Movie"

        hours, minutes = divmod(item.runtime_minutes, 60)
        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours}h"
        return f"{minutes}m"

    def filter_genre_names_for_category(self, category: str | None) -> list[str] | None:
        if not category:
            return None

        normalized = category.strip().lower()
        mapping = {
            "documentary": ["Documentary"],
            "documentaries": ["Documentary"],
            "science fiction": ["Science Fiction", "Sci-Fi & Fantasy"],
            "science-fiction": ["Science Fiction", "Sci-Fi & Fantasy"],
            "science": ["Science Fiction", "Sci-Fi & Fantasy", "Documentary"],
            "drama": ["Drama"],
            "action": ["Action", "Action & Adventure"],
            "comedy": ["Comedy"],
        }
        return mapping.get(normalized)

    def content_type_from_label(self, label: str | None) -> str | None:
        if not label:
            return None
        normalized = label.strip().lower()
        if normalized in {"movie", "movies"}:
            return "movie"
        if normalized in {"tv", "series", "shows"}:
            return "tv"
        return None

    def _preferred_video(self, videos: list[CatalogVideo]) -> CatalogVideo | None:
        if not videos:
            return None
        for video in videos:
            if video.site == "YouTube" and video.type == "Trailer" and video.official:
                return video
        for video in videos:
            if video.site == "YouTube" and video.type == "Trailer":
                return video
        for video in videos:
            if video.site in {"YouTube", "Vimeo"}:
                return video
        return None

    def video_embed_url(self, site: str, key: str) -> str | None:
        if site == "YouTube":
            return f"https://www.youtube.com/embed/{key}"
        if site == "Vimeo":
            return f"https://player.vimeo.com/video/{key}"
        return None
