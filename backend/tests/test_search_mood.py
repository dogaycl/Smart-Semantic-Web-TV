from datetime import date, datetime, timezone

from app.models.catalog_genre import CatalogGenre
from app.models.catalog_item import CatalogItem
from app.services.search.index_service import SearchIndexService
from app.services.search.service import SemanticSearchService

NEUTRAL_QUERY = "recommend a story to watch this week"


class DisabledEmbeddingService:
    """Forces the scorer onto lexical + category + mood signals only, so the test
    isolates the effect of the mood ranking profile."""

    def is_configured(self) -> bool:
        return False

    def embed_query(self, query: str) -> list[float]:  # pragma: no cover - not reached
        raise RuntimeError("embeddings disabled")

    def embed_document(self, *, title: str | None, text: str) -> list[float]:  # pragma: no cover
        raise RuntimeError("embeddings disabled")


def _make_item(db_session, *, slug, title, overview, genres, popularity=100.0):
    item = CatalogItem(
        slug=slug,
        content_type="movie",
        tmdb_id=abs(hash(slug)) % 1_000_000,
        title=title,
        original_title=title,
        overview=overview,
        release_date=date(2024, 1, 1),
        runtime_minutes=100,
        poster_url="https://example.com/poster.jpg",
        backdrop_url="https://example.com/backdrop.jpg",
        vote_average=7.5,
        popularity=popularity,
        original_language="en",
        status="Released",
        top_cast=["Lead Actor"],
        top_crew=["Director"],
        tmdb_url=f"https://www.themoviedb.org/movie/{abs(hash(slug)) % 1_000_000}",
        is_active=True,
        last_synced_at=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
    )
    db_session.add(item)
    db_session.flush()
    for index, genre in enumerate(genres, start=1):
        db_session.add(CatalogGenre(content_item_id=item.id, tmdb_genre_id=index, name=genre))
    db_session.commit()
    return item


def _seed_moody_catalog(db_session):
    _make_item(
        db_session,
        slug="movie-gentle-meadows",
        title="Gentle Meadows",
        overview="A calm and gentle heartwarming story about a cozy village. Wholesome and uplifting.",
        genres=["Family", "Animation"],
    )
    _make_item(
        db_session,
        slug="movie-laugh-factory",
        title="Laugh Factory",
        overview="A hilarious funny comedy story full of laughs, witty jokes and quirky characters.",
        genres=["Comedy"],
    )
    _make_item(
        db_session,
        slug="movie-turbo-strike",
        title="Turbo Strike",
        overview="An explosive high energy action story: a chase, an intense mission and an epic showdown.",
        genres=["Action", "Adventure"],
    )
    _make_item(
        db_session,
        slug="movie-paper-hearts",
        title="Paper Hearts",
        overview="A tender love story: a couple, a wedding and a passionate romance that spans years.",
        genres=["Romance"],
    )
    _make_item(
        db_session,
        slug="movie-the-cellar",
        title="The Cellar",
        overview="A terrifying haunted house horror story with a demon, a killer and a waking nightmare.",
        genres=["Horror", "Thriller"],
    )


def _titles_for_mood(db_session, mood):
    embedding_service = DisabledEmbeddingService()
    index_service = SearchIndexService(embedding_service=embedding_service)
    search_service = SemanticSearchService(embedding_service=embedding_service, index_service=index_service)
    index_service.sync_documents(db=db_session)
    response = search_service.search(
        db=db_session,
        user=None,
        query=NEUTRAL_QUERY,
        limit=5,
        window_hours=None,
        mood=mood,
    )
    return [result.title for result in response.results]


def test_each_mood_promotes_its_matching_genre_to_the_top(db_session):
    _seed_moody_catalog(db_session)

    assert _titles_for_mood(db_session, "relax")[0] == "Gentle Meadows"
    assert _titles_for_mood(db_session, "funny")[0] == "Laugh Factory"
    assert _titles_for_mood(db_session, "excited")[0] == "Turbo Strike"
    assert _titles_for_mood(db_session, "romantic")[0] == "Paper Hearts"
    assert _titles_for_mood(db_session, "scary")[0] == "The Cellar"


def test_moods_produce_meaningfully_different_rankings(db_session):
    _seed_moody_catalog(db_session)

    relax = _titles_for_mood(db_session, "relax")
    excited = _titles_for_mood(db_session, "excited")
    romantic = _titles_for_mood(db_session, "romantic")
    scary = _titles_for_mood(db_session, "scary")

    assert relax != excited
    assert relax != scary
    assert excited != romantic
    assert romantic != scary
    # The unmatched, "avoided" genre should not lead for an opposing mood.
    assert relax[0] != "Turbo Strike"
    assert scary[0] != "Gentle Meadows"


def test_search_without_mood_still_returns_results(db_session):
    _seed_moody_catalog(db_session)

    assert len(_titles_for_mood(db_session, None)) == 5


def test_unknown_mood_is_ignored_gracefully(db_session):
    _seed_moody_catalog(db_session)

    assert len(_titles_for_mood(db_session, "banana")) == 5
