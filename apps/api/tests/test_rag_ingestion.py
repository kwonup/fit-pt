from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.services.rag.ingestion import (
    KnowledgeDocumentMetadata,
    LocalKnowledgeLoader,
    ingest_knowledge_file,
    split_documents,
)


class FakeEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(index)] * self.dimensions for index, _ in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dimensions


class FakeStore:
    def __init__(self, existing_id: str | None = None) -> None:
        self.existing_id = existing_id
        self.documents: list[dict[str, Any]] = []
        self.chunks: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    def find_document_id(self, content_hash: str) -> str | None:
        return self.existing_id

    def insert_document(self, payload: dict[str, Any]) -> str:
        self.documents.append(payload)
        return "document-1"

    def insert_chunks(self, payloads: list[dict[str, Any]]) -> None:
        self.chunks.extend(payloads)

    def delete_document(self, document_id: str) -> None:
        self.deleted.append(document_id)


class KnowledgeIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "sample.md"
        self.path.write_text("근비대 원칙\n\n" + "점진적 과부하와 회복이 중요합니다. " * 20, encoding="utf-8")
        self.metadata = KnowledgeDocumentMetadata(
            title="근비대 기본 원칙",
            source_name="Fit-PT 테스트",
            document_type="note",
            language="ko",
            category="hypertrophy",
        )

    def test_loader_and_splitter_preserve_provenance(self) -> None:
        documents = LocalKnowledgeLoader(self.path).load()
        chunks = split_documents(documents, chunk_size=120, chunk_overlap=20)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(documents[0].metadata["file_name"], "sample.md")
        self.assertIn("start_index", chunks[0].metadata)

    def test_pdf_loader_keeps_one_based_page_number(self) -> None:
        pdf_path = Path(self.temp_dir.name) / "sample.pdf"
        pdf_path.write_bytes(b"test fixture")
        pages = [Mock(), Mock(), Mock()]
        pages[0].extract_text.return_value = "첫 페이지"
        pages[1].extract_text.return_value = ""
        pages[2].extract_text.return_value = "셋째 페이지"

        with patch(
            "app.services.rag.ingestion.PdfReader",
            return_value=SimpleNamespace(pages=pages),
        ):
            documents = LocalKnowledgeLoader(pdf_path).load()

        self.assertEqual([document.metadata["page"] for document in documents], [1, 3])

    def test_ingest_stores_document_chunks_and_embeddings(self) -> None:
        store = FakeStore()
        embeddings = FakeEmbeddings()

        result = ingest_knowledge_file(
            self.path,
            self.metadata,
            store=store,
            embeddings=embeddings,
            chunk_size=120,
            chunk_overlap=20,
            embedding_batch_size=2,
        )

        self.assertFalse(result.skipped)
        self.assertEqual(result.chunk_count, len(store.chunks))
        self.assertEqual(store.documents[0]["metadata"], {"category": "hypertrophy"})
        self.assertEqual(store.chunks[0]["document_id"], "document-1")
        self.assertEqual(len(store.chunks[0]["embedding"]), settings.EMBEDDING_DIMENSIONS)
        self.assertEqual(
            [chunk["chunk_index"] for chunk in store.chunks],
            list(range(result.chunk_count)),
        )
        self.assertGreater(len(embeddings.calls), 1)

    def test_duplicate_content_is_skipped_before_embedding(self) -> None:
        store = FakeStore(existing_id="existing-document")
        embeddings = FakeEmbeddings()

        result = ingest_knowledge_file(
            self.path,
            self.metadata,
            store=store,
            embeddings=embeddings,
        )

        self.assertTrue(result.skipped)
        self.assertEqual(result.document_id, "existing-document")
        self.assertEqual(embeddings.calls, [])
        self.assertEqual(store.documents, [])

    def test_dimension_mismatch_rolls_back_document(self) -> None:
        store = FakeStore()

        with self.assertRaisesRegex(RuntimeError, "embedding 차원"):
            ingest_knowledge_file(
                self.path,
                self.metadata,
                store=store,
                embeddings=FakeEmbeddings(dimensions=3),
            )

        self.assertEqual(store.deleted, ["document-1"])
        self.assertEqual(store.chunks, [])

    def test_invalid_overlap_is_rejected(self) -> None:
        documents = LocalKnowledgeLoader(self.path).load()

        with self.assertRaises(ValueError):
            split_documents(documents, chunk_size=100, chunk_overlap=100)


if __name__ == "__main__":
    unittest.main()
