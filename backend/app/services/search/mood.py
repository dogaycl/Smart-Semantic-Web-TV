"""Mood ranking profiles for the "Choose by mood" discovery control.

Each profile maps a mood id to real, metadata-driven ranking signals. The semantic
search scorer combines a mood component (genre affinity + keyword affinity minus
avoidance) with its existing lexical / semantic / category / profile signals, so
switching moods measurably re-orders results drawn from the live database instead
of returning a fixed list of titles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.search.query_parser import tokenize_text


@dataclass(slots=True)
class MoodProfile:
    mood_id: str
    label: str
    # genre / category label -> positive weight
    boost_genres: dict[str, float] = field(default_factory=dict)
    # free tokens expected in the overview / description / searchable text
    boost_keywords: set[str] = field(default_factory=set)
    # genre / category label -> penalty weight
    avoid_genres: dict[str, float] = field(default_factory=dict)
    avoid_keywords: set[str] = field(default_factory=set)

    def _max_boost(self) -> float:
        return max([*self.boost_genres.values(), 1.0])


MOOD_PROFILES: dict[str, MoodProfile] = {
    "relax": MoodProfile(
        mood_id="relax",
        label="Relax",
        boost_genres={
            "family": 1.0,
            "animation": 0.85,
            "romance": 0.75,
            "music": 0.7,
            "comedy": 0.55,
            "documentary": 0.35,
        },
        boost_keywords={
            "calm",
            "calming",
            "gentle",
            "cozy",
            "cosy",
            "heartwarming",
            "wholesome",
            "feel",
            "good",
            "light",
            "lighthearted",
            "soothing",
            "relaxing",
            "peaceful",
            "nature",
            "charming",
            "sweet",
            "uplifting",
        },
        avoid_genres={
            "horror": 1.0,
            "thriller": 0.8,
            "war": 0.7,
            "crime": 0.55,
            "mystery": 0.35,
        },
        avoid_keywords={"violent", "brutal", "gory", "disturbing", "terror", "bloody", "intense"},
    ),
    "funny": MoodProfile(
        mood_id="funny",
        label="Funny",
        boost_genres={
            "comedy": 1.0,
            "animation": 0.55,
            "family": 0.5,
            "romance": 0.3,
            "entertainment": 0.6,
        },
        boost_keywords={
            "funny",
            "hilarious",
            "comedy",
            "comedic",
            "humor",
            "humour",
            "laugh",
            "laughs",
            "parody",
            "sitcom",
            "witty",
            "satire",
            "quirky",
            "goofy",
            "absurd",
        },
        avoid_genres={"horror": 0.6, "war": 0.5, "documentary": 0.3, "drama": 0.25},
        avoid_keywords={"harrowing", "bleak", "tragic", "somber"},
    ),
    "excited": MoodProfile(
        mood_id="excited",
        label="Excited",
        boost_genres={
            "action": 1.0,
            "adventure": 0.9,
            "sport": 0.95,
            "sports": 0.95,
            "thriller": 0.8,
            "science fiction": 0.6,
            "crime": 0.5,
            "war": 0.5,
        },
        boost_keywords={
            "action",
            "explosive",
            "high",
            "energy",
            "fast",
            "paced",
            "adrenaline",
            "chase",
            "battle",
            "epic",
            "intense",
            "thrilling",
            "sports",
            "championship",
            "race",
            "showdown",
            "heist",
            "mission",
        },
        avoid_genres={"documentary": 0.35, "music": 0.2},
        avoid_keywords={"slow", "meditative", "quiet", "gentle", "sleepy"},
    ),
    "romantic": MoodProfile(
        mood_id="romantic",
        label="Romantic",
        boost_genres={
            "romance": 1.0,
            "drama": 0.45,
            "comedy": 0.45,
            "music": 0.3,
        },
        boost_keywords={
            "love",
            "romance",
            "romantic",
            "relationship",
            "wedding",
            "couple",
            "heart",
            "heartfelt",
            "affair",
            "passion",
            "passionate",
            "date",
            "kiss",
            "soulmate",
            "tender",
            "sweetheart",
        },
        avoid_genres={"horror": 0.9, "war": 0.6, "action": 0.35, "documentary": 0.3},
        avoid_keywords={"brutal", "gory", "violent", "terrifying"},
    ),
    "scary": MoodProfile(
        mood_id="scary",
        label="Scary",
        boost_genres={
            "horror": 1.0,
            "thriller": 0.8,
            "mystery": 0.6,
            "science fiction": 0.3,
        },
        boost_keywords={
            "horror",
            "terrifying",
            "terror",
            "scary",
            "haunted",
            "haunting",
            "ghost",
            "demon",
            "demonic",
            "killer",
            "nightmare",
            "dread",
            "supernatural",
            "creepy",
            "chilling",
            "sinister",
            "slasher",
            "monster",
            "possessed",
        },
        avoid_genres={"comedy": 0.55, "family": 0.7, "animation": 0.4, "romance": 0.35},
        avoid_keywords={"heartwarming", "wholesome", "cozy", "cheerful", "uplifting", "feel"},
    ),
}


def resolve_mood(mood: str | None) -> MoodProfile | None:
    if not mood:
        return None
    return MOOD_PROFILES.get(mood.strip().lower())


def score_document_for_mood(
    *,
    profile: MoodProfile,
    genres: list[str],
    category_label: str | None,
    document_tokens: set[str],
) -> tuple[float, str]:
    """Return a mood affinity score in roughly [-0.5, 1.0] plus a short reason."""

    haystack_genres = {value.strip().lower() for value in genres if value}
    if category_label:
        haystack_genres.add(category_label.strip().lower())

    boost = 0.0
    matched_genres: list[str] = []
    for genre, weight in profile.boost_genres.items():
        if genre in haystack_genres:
            boost += weight
            matched_genres.append(genre)
    genre_score = min(boost / profile._max_boost(), 1.0) if boost else 0.0

    keyword_hits = profile.boost_keywords & document_tokens
    keyword_score = min(len(keyword_hits) / 3.0, 1.0)

    penalty = 0.0
    for genre, weight in profile.avoid_genres.items():
        if genre in haystack_genres:
            penalty += weight
    penalty += 0.25 * len(profile.avoid_keywords & document_tokens)
    penalty_score = min(penalty / profile._max_boost(), 1.0)

    score = (genre_score * 0.65) + (keyword_score * 0.35) - (penalty_score * 0.6)
    score = max(-0.5, min(score, 1.0))

    if matched_genres:
        reason = f"{profile.label} mood: {matched_genres[0].title()} content."
    elif keyword_hits:
        reason = f"{profile.label} mood: matches {', '.join(sorted(keyword_hits)[:2])}."
    elif score < 0:
        reason = ""
    else:
        reason = ""
    return round(score, 6), reason


__all__ = ["MOOD_PROFILES", "MoodProfile", "resolve_mood", "score_document_for_mood", "tokenize_text"]
