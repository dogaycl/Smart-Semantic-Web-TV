from app.db.base_class import Base


from app.models.user import User  # noqa: E402,F401
from app.models.user_profile import UserProfile  # noqa: E402,F401
from app.models.favorite import Favorite  # noqa: E402,F401
from app.models.watch_history import WatchHistory  # noqa: E402,F401
from app.models.channel import Channel  # noqa: E402,F401
from app.models.epg_entry import EPGEntry  # noqa: E402,F401
from app.models.catalog_item import CatalogItem  # noqa: E402,F401
from app.models.catalog_genre import CatalogGenre  # noqa: E402,F401
from app.models.catalog_season import CatalogSeason  # noqa: E402,F401
from app.models.catalog_video import CatalogVideo  # noqa: E402,F401
from app.models.playback_source import PlaybackSource  # noqa: E402,F401
from app.models.search_document import SearchDocument  # noqa: E402,F401
from app.models.viewing_plan import ViewingPlan  # noqa: E402,F401
from app.models.viewing_plan_item import ViewingPlanItem  # noqa: E402,F401
from app.models.watch_room import WatchRoom  # noqa: E402,F401
from app.models.watch_room_participant import WatchRoomParticipant  # noqa: E402,F401
from app.models.watch_room_message import WatchRoomMessage  # noqa: E402,F401
