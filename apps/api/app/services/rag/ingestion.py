from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator, Literal, Protocol, Sequence

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from supabase import Client

from app.core.config import settings

DocumentType = Literal["paper", "guideline", "article", "note", "other"]
SUPPORTED_SUFFIXES = {".md", ".pdf", ".txt"}
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_EMBEDDING_BATCH_SIZE = 64


class KnowledgeStore(Protocol):
    def find_document_id(self, content_hash: str) -> str | None: ...

    def insert_document(self, payload: dict[str, Any]) -> str: ...

    def insert_chunks(self, payloads: list[dict[str, Any]]) -> None: ...

    def delete_document(self, document_id: str) -> None: ...


@dataclass(frozen=True)
class KnowledgeDocumentMetadata:
    title: str
    source_name: str
    source_url: str | None = None
    document_type: DocumentType = "other"
    language: str = "unknown"
    published_at: str | None = None
    license_info: str | None = None
    category: str | None = None


@dataclass(frozen=True)
class IngestionResult:
    document_id: str
    chunk_count: int
    content_hash: str
    skipped: bool


class LocalKnowledgeLoader(BaseLoader):
    """로컬 PDF, Markdown, 텍스트 파일을 LangChain Document로 변환한다."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path.resolve()

    def lazy_load(self) -> Iterator[Document]:
        if not self.file_path.is_file():
            raise FileNotFoundError(f"지식 문서를 찾을 수 없습니다: {self.file_path}")

        suffix = self.file_path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix} (지원: {supported})")

        if suffix == ".pdf":
            yield from self._lazy_load_pdf()
            return

        content = self.file_path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"문서에 추출 가능한 텍스트가 없습니다: {self.file_path}")
        yield Document(
            page_content=content,
            metadata={"source": str(self.file_path), "file_name": self.file_path.name},
        )

    def _lazy_load_pdf(self) -> Iterator[Document]:
        extracted = False
        reader = PdfReader(str(self.file_path))
        for page_index, page in enumerate(reader.pages):
            content = (page.extract_text() or "").strip()
            if not content:
                continue
            extracted = True
            yield Document(
                page_content=content,
                metadata={
                    "source": str(self.file_path),
                    "file_name": self.file_path.name,
                    "page": page_index + 1,
                },
            )
        if not extracted:
            raise ValueError(
                "PDF에서 텍스트를 추출할 수 없습니다. 스캔 PDF는 OCR 후 다시 시도하세요."
            )


class SupabaseKnowledgeStore:
    def __init__(self, client: Client) -> None:
        self.client = client

    def find_document_id(self, content_hash: str) -> str | None:
        response = (
            self.client.table("knowledge_documents")
            .select("id")
            .eq("content_hash", content_hash)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return str(rows[0]["id"]) if rows else None

    def insert_document(self, payload: dict[str, Any]) -> str:
        response = self.client.table("knowledge_documents").insert(payload).execute()
        rows = response.data or []
        if not rows:
            raise RuntimeError("knowledge_documents 저장 결과에 문서 ID가 없습니다.")
        return str(rows[0]["id"])

    def insert_chunks(self, payloads: list[dict[str, Any]]) -> None:
        self.client.table("knowledge_chunks").insert(payloads).execute()

    def delete_document(self, document_id: str) -> None:
        self.client.table("knowledge_documents").delete().eq("id", document_id).execute()


def build_embedding_model() -> Embeddings:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )


def split_documents(
    documents: Sequence[Document],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    if chunk_size <= 0:
        raise ValueError("chunk_size는 1 이상이어야 합니다.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap은 0 이상, chunk_size 미만이어야 합니다.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        separators=["\n\n", "\n", ". ", "。", ".", " ", ""],
    )
    return splitter.split_documents(list(documents))


def ingest_knowledge_file(
    file_path: Path,
    metadata: KnowledgeDocumentMetadata,
    *,
    store: KnowledgeStore,
    embeddings: Embeddings,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    embedding_batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> IngestionResult:
    if embedding_batch_size <= 0:
        raise ValueError("embedding_batch_size는 1 이상이어야 합니다.")

    documents = LocalKnowledgeLoader(file_path).load()
    content_hash = _content_hash(documents)
    existing_id = store.find_document_id(content_hash)
    if existing_id:
        return IngestionResult(existing_id, 0, content_hash, skipped=True)

    chunks = split_documents(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not chunks:
        raise ValueError("분할 후 저장할 chunk가 없습니다.")

    document_id = store.insert_document(_document_payload(metadata, content_hash))
    try:
        for start in range(0, len(chunks), embedding_batch_size):
            batch = chunks[start : start + embedding_batch_size]
            vectors = embeddings.embed_documents([chunk.page_content for chunk in batch])
            if len(vectors) != len(batch):
                raise RuntimeError("embedding 결과 개수가 요청한 chunk 개수와 다릅니다.")

            payloads: list[dict[str, Any]] = []
            for offset, (chunk, vector) in enumerate(zip(batch, vectors, strict=True)):
                if len(vector) != settings.EMBEDDING_DIMENSIONS:
                    raise RuntimeError(
                        "embedding 차원이 DB 규격과 다릅니다: "
                        f"expected={settings.EMBEDDING_DIMENSIONS}, actual={len(vector)}"
                    )
                payloads.append(
                    {
                        "document_id": document_id,
                        "chunk_index": start + offset,
                        "content": chunk.page_content,
                        "embedding": vector,
                        "metadata": _chunk_metadata(chunk),
                    }
                )
            store.insert_chunks(payloads)
    except Exception:
        store.delete_document(document_id)
        raise

    return IngestionResult(document_id, len(chunks), content_hash, skipped=False)


def _content_hash(documents: Sequence[Document]) -> str:
    normalized = "\n\n".join(document.page_content.strip() for document in documents)
    return sha256(normalized.encode("utf-8")).hexdigest()


def _document_payload(
    metadata: KnowledgeDocumentMetadata,
    content_hash: str,
) -> dict[str, Any]:
    return {
        "title": metadata.title,
        "source_name": metadata.source_name,
        "source_url": metadata.source_url,
        "document_type": metadata.document_type,
        "language": metadata.language,
        "published_at": metadata.published_at,
        "license_info": metadata.license_info,
        "content_hash": content_hash,
        "metadata": {"category": metadata.category} if metadata.category else {},
    }


def _chunk_metadata(chunk: Document) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("page", "start_index"):
        if key in chunk.metadata:
            result[key] = chunk.metadata[key]
    return result
