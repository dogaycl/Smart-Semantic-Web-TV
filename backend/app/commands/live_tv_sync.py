import argparse

from app.db.session import SessionLocal
from app.services.epg.service import EPGService
from app.services.live_tv.sync_service import LiveTVSyncService


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Smart Semantic Web TV live channels and EPG data.")
    parser.add_argument(
        "command",
        choices=["sync-channels", "refresh-live-status", "sync-epg"],
        help="Synchronization action to execute.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=12,
        help="EPG lookahead window in hours for sync-epg.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    sync_service = LiveTVSyncService()
    epg_service = EPGService()
    try:
        if args.command == "sync-channels":
            sync_service.sync_channels(db=db)
        elif args.command == "refresh-live-status":
            sync_service.ensure_ready(db=db)
            sync_service.refresh_live_status(db=db)
        elif args.command == "sync-epg":
            sync_service.ensure_ready(db=db)
            start, end = epg_service.default_window(hours=args.window_hours)
            sync_service.sync_epg(db=db, window_start=start, window_end=end)
    finally:
        db.close()


if __name__ == "__main__":
    main()
