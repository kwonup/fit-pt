from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import settings
from app.core.deps import get_supabase
from app.services.rag.retriever import build_knowledge_retriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Supabase에 적재된 운동 전문지식을 의미 기반으로 검색합니다."
    )
    parser.add_argument("question", help="검색할 운동 질문")
    parser.add_argument("--top-k", type=int, default=settings.RAG_TOP_K)
    parser.add_argument(
        "--threshold",
        type=float,
        default=settings.RAG_MATCH_THRESHOLD,
        help="최소 cosine similarity (0~1)",
    )
    parser.add_argument("--category", help="문서 category metadata 필터")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata_filter = {"category": args.category} if args.category else {}
    retriever = build_knowledge_retriever(
        get_supabase(),
        top_k=args.top_k,
        match_threshold=args.threshold,
        metadata_filter=metadata_filter,
    )
    documents = retriever.invoke(args.question)

    if not documents:
        print("기준을 충족하는 운동 지식 검색 결과가 없습니다.")
        return 0

    for index, document in enumerate(documents, start=1):
        metadata = document.metadata
        page = f", page={metadata['page']}" if "page" in metadata else ""
        print(
            f"[{index}] similarity={metadata['similarity']:.4f}, "
            f"title={metadata.get('title', '-')}, "
            f"source={metadata.get('source_name', '-')}{page}"
        )
        print(document.page_content)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
