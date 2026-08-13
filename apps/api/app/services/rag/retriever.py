from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field
from supabase import Client

from app.core.config import settings
from app.services.rag.ingestion import build_embedding_model


@runtime_checkable
class KnowledgeSearchStore(Protocol):
    def match_chunks(
        self,
        query_embedding: list[float],
        *,
        match_threshold: float,
        match_count: int,
        metadata_filter: dict[str, Any],
    ) -> list[dict[str, Any]]: ...


class SupabaseKnowledgeSearchStore:
    """Supabase의 match_knowledge_chunks RPC 호출을 캡슐화한다."""

    def __init__(self, client: Client) -> None:
        self.client = client

    def match_chunks(
        self,
        query_embedding: list[float],
        *,
        match_threshold: float,
        match_count: int,
        metadata_filter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        response = self.client.rpc(
            "match_knowledge_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
                "filter": metadata_filter,
            },
        ).execute()
        rows = response.data or []
        if not isinstance(rows, list):
            raise RuntimeError("RAG 검색 결과가 예상한 목록 형식이 아닙니다.")
        return rows


class FitnessKnowledgeRetriever(BaseRetriever):
    """질문과 의미가 가까운 운동 전문지식을 LangChain Document로 반환한다."""

    store: KnowledgeSearchStore
    embeddings: Embeddings
    top_k: int = Field(default=4, ge=1, le=20)
    match_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("검색 질문은 비어 있을 수 없습니다.")

        query_embedding = self.embeddings.embed_query(normalized_query)
        if len(query_embedding) != settings.EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                "질문 embedding 차원이 DB 규격과 다릅니다: "
                f"expected={settings.EMBEDDING_DIMENSIONS}, actual={len(query_embedding)}"
            )

        rows = self.store.match_chunks(
            query_embedding,
            match_threshold=self.match_threshold,
            match_count=self.top_k,
            metadata_filter=self.metadata_filter,
        )
        return [_row_to_document(row) for row in rows]


def build_knowledge_retriever(
    client: Client,
    *,
    embeddings: Embeddings | None = None,
    top_k: int | None = None,
    match_threshold: float | None = None,
    metadata_filter: dict[str, Any] | None = None,
) -> FitnessKnowledgeRetriever:
    return FitnessKnowledgeRetriever(
        store=SupabaseKnowledgeSearchStore(client),
        embeddings=embeddings or build_embedding_model(),
        top_k=settings.RAG_TOP_K if top_k is None else top_k,
        match_threshold=(
            settings.RAG_MATCH_THRESHOLD
            if match_threshold is None
            else match_threshold
        ),
        metadata_filter=metadata_filter or {},
    )


def _row_to_document(row: dict[str, Any]) -> Document:
    content = row.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("RAG 검색 결과에 유효한 content가 없습니다.")

    raw_metadata = row.get("metadata") or {}
    if not isinstance(raw_metadata, dict):
        raise RuntimeError("RAG 검색 결과 metadata가 객체 형식이 아닙니다.")

    metadata = dict(raw_metadata)
    metadata.update(
        {
            "chunk_id": str(row["id"]),
            "document_id": str(row["document_id"]),
            "similarity": float(row["similarity"]),
        }
    )
    return Document(
        id=str(row["id"]),
        page_content=content,
        metadata=metadata,
    )
