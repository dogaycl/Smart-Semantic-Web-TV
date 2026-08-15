import argparse

from app.db.session import SessionLocal
from app.services.catalog.sync_service import CatalogSyncService


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Smart Semantic Web TV movie and TV catalog from TMDB.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional target number of catalog items to sync.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    sync_service = CatalogSyncService()
    try:
        sync_service.sync_catalog(db=db, target_items=args.limit)
    finally:
        db.close()


if __name__ == "__main__":
    main()
