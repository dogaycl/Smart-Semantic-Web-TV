from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re


CATEGORY_SYNONYMS = {
    "documentary": {"documentary", "documentaries", "doc", "docs"},
    "science fiction": {"science fiction", "sci-fi", "sci fi", "science", "space", "technology"},
    "technology": {"technology", "tech", "ai", "artificial intelligence"},
    "comedy": {"comedy", "funny", "humor", "humour"},
    "drama": {"drama", "dramatic"},
    "action": {"action", "adventure", "thrilling"},
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


@dataclass(slots=True)
class QueryIntent:
    raw_query: str
    normalized_query: str
    keywords: list[str]
    expanded_terms: list[str]
    preferred_categories: list[str] = field(default_factory=list)
    max_duration_minutes: int | None = None
    prioritize_live: bool = False
    window_start: datetime | None = None
    window_end: datetime | None = None


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def tokenize_text(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", normalize_text(value)) if len(token) > 1]


class QueryParser:
    def parse(self, query: str, *, now: datetime | None = None, window_hours: int | None = None) -> QueryIntent:
        normalized = normalize_text(query)
        current = now or datetime.now(timezone.utc)
        categories = self._extract_categories(normalized)
        max_duration = self._extract_max_duration_minutes(normalized)
        prioritize_live, window_start, window_end = self._extract_time_window(normalized, current, window_hours)
        keywords = tokenize_text(normalized)
        expanded_terms = self._expand_terms(keywords, categories)
        return QueryIntent(
            raw_query=query,
            normalized_query=normalized,
            keywords=keywords,
            expanded_terms=expanded_terms,
            preferred_categories=categories,
            max_duration_minutes=max_duration,
            prioritize_live=prioritize_live,
            window_start=window_start,
            window_end=window_end,
        )

    def _extract_categories(self, normalized: str) -> list[str]:
        matched: list[str] = []
        for category, synonyms in CATEGORY_SYNONYMS.items():
            if any(term in normalized for term in synonyms):
                matched.append(category.title())
        return matched

    def _extract_max_duration_minutes(self, normalized: str) -> int | None:
        match = re.search(
            r"(?:under|less than|below)\s+(?P<value>\d+|one|two|three|four|five|six)\s+(?P<unit>hours?|hrs?|minutes?|mins?)",
            normalized,
        )
        if not match:
            return None

        raw_value = match.group("value")
        value = int(raw_value) if raw_value.isdigit() else NUMBER_WORDS.get(raw_value, 0)
        if value <= 0:
            return None

        unit = match.group("unit")
        if unit.startswith("hour") or unit.startswith("hr"):
            return value * 60
        return value

    def _extract_time_window(
        self,
        normalized: str,
        now: datetime,
        explicit_window_hours: int | None,
    ) -> tuple[bool, datetime | None, datetime | None]:
        if explicit_window_hours:
            return True, now, now + timedelta(hours=explicit_window_hours)

        local_now = now.astimezone()

        if "tonight" in normalized or "this evening" in normalized:
            end_local = local_now.replace(hour=23, minute=59, second=59, microsecond=0)
            return True, now, end_local.astimezone(timezone.utc)

        if "today" in normalized:
            end_local = local_now.replace(hour=23, minute=59, second=59, microsecond=0)
            return True, now, end_local.astimezone(timezone.utc)

        if "weekend" in normalized:
            return True, now, now + timedelta(days=2)

        if "live" in normalized or "airing" in normalized or "on now" in normalized:
            return True, now, now + timedelta(hours=6)

        return False, None, None

    def _expand_terms(self, keywords: list[str], categories: list[str]) -> list[str]:
        expanded = set(keywords)
        for category in categories:
            for term in CATEGORY_SYNONYMS.get(category.lower(), set()):
                expanded.update(tokenize_text(term))
        if "ai" in expanded:
            expanded.update({"artificial", "intelligence", "technology", "tech"})
        if "space" in expanded:
            expanded.update({"science", "documentary", "cosmos"})
        if "funny" in expanded:
            expanded.update({"comedy", "humor"})
        return sorted(expanded)
