from __future__ import annotations

import math

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.types import vector_literal
from app.models.search_document import SearchDocument


class SearchDocumentRepository:
    def list_all(self, *, db: Session) -> list[SearchDocument]:
        statement = select(SearchDocument).order_by(SearchDocument.id.asc())
        return list(db.scalars(statement).all())

    def list_active(self, *, db: Session) -> list[SearchDocument]:
        statement = (
            select(SearchDocument)
            .where(SearchDocument.is_active.is_(True))
            .order_by(SearchDocument.document_type.asc(), SearchDocument.title.asc())
        )
        return list(db.scalars(statement).all())

    def list_by_source_keys(self, *, db: Session, source_keys: list[str]) -> list[SearchDocument]:
        if not source_keys:
            return []
        statement = select(SearchDocument).where(SearchDocument.source_key.in_(source_keys))
        return list(db.scalars(statement).all())

    def create(self, **kwargs) -> SearchDocument:
        return SearchDocument(**kwargs)

    def semantic_candidates(
        self,
        *,
        db: Session,
        query_embedding: list[float],
        limit: int,
    ) -> list[tuple[SearchDocument, float]]:
        bind = db.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            documents = [
                document
                for document in self.list_active(db=db)
                if document.embedding is not None
            ]
            ranked = [
                (document, self._cosine_similarity(query_embedding, document.embedding))
                for document in documents
            ]
            ranked.sort(key=lambda item: (-item[1], item[0].title.lower()))
            return ranked[:limit]

        rows = db.execute(
            text(
                """
                SELECT id, 1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity
                FROM search_documents
                WHERE is_active = true
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
                """
            ),
            {
                "query_embedding": vector_literal(query_embedding),
                "limit": limit,
            },
        ).mappings().all()

        if not rows:
            return []

        ids = [int(row["id"]) for row in rows]
        documents = list(db.scalars(select(SearchDocument).where(SearchDocument.id.in_(ids))).all())
        document_map = {document.id: document for document in documents}
        return [
            (document_map[int(row["id"])], float(row["similarity"] or 0.0))
            for row in rows
            if int(row["id"]) in document_map
        ]

    def _cosine_similarity(self, left: list[float], right: list[float] | None) -> float:
        if right is None or len(left) != len(right):
            return 0.0

        numerator = sum(float(a) * float(b) for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(float(a) * float(a) for a in left))
        right_norm = math.sqrt(sum(float(b) * float(b) for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
