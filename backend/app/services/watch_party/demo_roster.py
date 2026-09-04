"""Illustrative "friends" shown in every watch room.

These are not real accounts. They exist so the participant list is never a lonely
single row: the host sees three room regulars listed underneath them, all offline
(dimmed, no green dot), as if they were also in the room but not currently watching.
Toggle with the ``watch_party_demo_participants`` setting.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.watch_party import WatchRoomParticipantRead

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

# (user_id, username, display_name, avatar preset, is_connected)
# Three room regulars, all offline.
_DEMO_FRIENDS: list[tuple[int, str, str, str, bool]] = [
    (-101, "dogakaya", "Doğa Kaya", "preset:rose", False),
    (-102, "elayildiz", "Ela Yıldız", "preset:mint", False),
    (-103, "keremaslan", "Kerem Aslan", "preset:sky", False),
]


def demo_participants() -> list[WatchRoomParticipantRead]:
    now = datetime.now(timezone.utc)
    entries: list[WatchRoomParticipantRead] = []
    for user_id, username, display_name, avatar, is_connected in _DEMO_FRIENDS:
        entries.append(
            WatchRoomParticipantRead(
                user_id=user_id,
                username=username,
                display_name=display_name,
                avatar_url=avatar,
                is_host=False,
                joined_at=_NOW,
                last_seen_at=now if is_connected else now - timedelta(minutes=8),
                is_connected=is_connected,
            )
        )
    return entries
