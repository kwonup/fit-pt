from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.deps import get_supabase
from app.services.rag.ingestion import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    KnowledgeDocumentMetadata,
    SupabaseKnowledgeStore,
    build_embedding_model,
    ingest_knowledge_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="운동 전문지식 문서를 분할·임베딩하여 Supabase에 적재합니다."
    )
    parser.add_argument("file", type=Path, help="UTF-8 .md/.txt 또는 텍스트 기반 .pdf 경로")
    parser.add_argument("--title", required=True, help="문서 제목")
    parser.add_argument("--source-name", required=True, help="기관·저널·출판처 이름")
    parser.add_argument("--source-url", help="원문 URL 또는 DOI URL")
    parser.add_argument(
        "--document-type",
        choices=("paper", "guideline", "article", "note", "other"),
        default="other",
    )
    parser.add_argument("--language", default="unknown", help="예: ko, en")
    parser.add_argument("--published-at", help="발행일(YYYY-MM-DD)")
    parser.add_argument("--license-info", help="라이선스·이용 조건")
    parser.add_argument("--category", help="예: hypertrophy, running, recovery")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = KnowledgeDocumentMetadata(
        title=args.title,
        source_name=args.source_name,
        source_url=args.source_url,
        document_type=args.document_type,
        language=args.language,
        published_at=args.published_at,
        license_info=args.license_info,
        category=args.category,
    )
    result = ingest_knowledge_file(
        args.file,
        metadata,
        store=SupabaseKnowledgeStore(get_supabase()),
        embeddings=build_embedding_model(),
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    if result.skipped:
        print(f"이미 적재된 문서입니다: document_id={result.document_id}")
    else:
        print(
            "지식 문서 적재 완료: "
            f"document_id={result.document_id}, chunks={result.chunk_count}, "
            f"content_hash={result.content_hash}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
