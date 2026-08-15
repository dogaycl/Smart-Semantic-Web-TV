from app.db.session import SessionLocal
from app.services.search.index_service import SearchIndexService


def main() -> None:
    db = SessionLocal()
    service = SearchIndexService()
    try:
        service.sync_documents(db=db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
