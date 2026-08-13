from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.services.rag.retriever import (
    FitnessKnowledgeRetriever,
    SupabaseKnowledgeSearchStore,
)


class FakeEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions
        self.query_calls: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dimensions for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return [0.5] * self.dimensions


class FakeSearchStore:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[dict[str, Any]] = []

    def match_chunks(
        self,
        query_embedding: list[float],
        *,
        match_threshold: float,
        match_count: int,
        metadata_filter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
                "metadata_filter": metadata_filter,
            }
        )
        return self.rows


class FitnessKnowledgeRetrieverTests(unittest.TestCase):
    def test_supabase_store_calls_match_rpc_with_search_options(self) -> None:
        client = Mock()
        client.rpc.return_value.execute.return_value = SimpleNamespace(data=[])
        store = SupabaseKnowledgeSearchStore(client)
        embedding = [0.5] * settings.EMBEDDING_DIMENSIONS

        rows = store.match_chunks(
            embedding,
            match_threshold=0.72,
            match_count=5,
            metadata_filter={"category": "running"},
        )

        self.assertEqual(rows, [])
        client.rpc.assert_called_once_with(
            "match_knowledge_chunks",
            {
                "query_embedding": embedding,
                "match_threshold": 0.72,
                "match_count": 5,
                "filter": {"category": "running"},
            },
        )

    def test_retriever_embeds_query_and_returns_documents_with_provenance(self) -> None:
        embeddings = FakeEmbeddings()
        store = FakeSearchStore(
            [
                {
                    "id": "chunk-1",
                    "document_id": "document-1",
                    "content": "점진적 과부하는 수행 능력에 맞춰 부하를 높이는 원칙입니다.",
                    "metadata": {
                        "title": "점진적 과부하",
                        "source_name": "Fit-PT 프로젝트",
                        "category": "progressive-overload",
                        "page": 2,
                    },
                    "similarity": 0.89,
                }
            ]
        )
        retriever = FitnessKnowledgeRetriever(
            store=store,
            embeddings=embeddings,
            top_k=3,
            match_threshold=0.75,
            metadata_filter={"category": "progressive-overload"},
        )

        documents = retriever.invoke("  벤치프레스 중량은 언제 올려?  ")

        self.assertEqual(embeddings.query_calls, ["벤치프레스 중량은 언제 올려?"])
        self.assertEqual(len(store.calls[0]["query_embedding"]), settings.EMBEDDING_DIMENSIONS)
        self.assertEqual(store.calls[0]["match_count"], 3)
        self.assertEqual(store.calls[0]["match_threshold"], 0.75)
        self.assertEqual(
            store.calls[0]["metadata_filter"],
            {"category": "progressive-overload"},
        )
        self.assertEqual(documents[0].id, "chunk-1")
        self.assertEqual(documents[0].metadata["document_id"], "document-1")
        self.assertEqual(documents[0].metadata["title"], "점진적 과부하")
        self.assertEqual(documents[0].metadata["similarity"], 0.89)

    def test_no_matches_returns_empty_documents(self) -> None:
        retriever = FitnessKnowledgeRetriever(
            store=FakeSearchStore(),
            embeddings=FakeEmbeddings(),
        )

        self.assertEqual(retriever.invoke("근비대 휴식 시간은?"), [])

    def test_async_langchain_interface_returns_documents(self) -> None:
        store = FakeSearchStore(
            [
                {
                    "id": "chunk-1",
                    "document_id": "document-1",
                    "content": "검색 내용",
                    "metadata": {},
                    "similarity": 0.8,
                }
            ]
        )
        retriever = FitnessKnowledgeRetriever(
            store=store,
            embeddings=FakeEmbeddings(),
        )

        documents = asyncio.run(retriever.ainvoke("점진적 과부하란?"))

        self.assertEqual(documents[0].page_content, "검색 내용")

    def test_blank_query_is_rejected_before_embedding(self) -> None:
        embeddings = FakeEmbeddings()
        store = FakeSearchStore()
        retriever = FitnessKnowledgeRetriever(store=store, embeddings=embeddings)

        with self.assertRaisesRegex(ValueError, "비어 있을 수 없습니다"):
            retriever.invoke("   ")

        self.assertEqual(embeddings.query_calls, [])
        self.assertEqual(store.calls, [])

    def test_embedding_dimension_mismatch_is_rejected_before_search(self) -> None:
        store = FakeSearchStore()
        retriever = FitnessKnowledgeRetriever(
            store=store,
            embeddings=FakeEmbeddings(dimensions=3),
        )

        with self.assertRaisesRegex(RuntimeError, "embedding 차원"):
            retriever.invoke("점진적 과부하란?")

        self.assertEqual(store.calls, [])

    def test_invalid_result_metadata_is_rejected(self) -> None:
        store = FakeSearchStore(
            [
                {
                    "id": "chunk-1",
                    "document_id": "document-1",
                    "content": "검색 내용",
                    "metadata": "invalid",
                    "similarity": 0.8,
                }
            ]
        )
        retriever = FitnessKnowledgeRetriever(
            store=store,
            embeddings=FakeEmbeddings(),
        )

        with self.assertRaisesRegex(RuntimeError, "metadata"):
            retriever.invoke("질문")


if __name__ == "__main__":
    unittest.main()
