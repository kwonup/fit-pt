from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.ai.question_router import build_question_router, get_route_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit-PT 사용자 질문의 intent를 분류합니다.")
    parser.add_argument("question", help="분류할 사용자 질문")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_question_router().route(args.question)
    plan = get_route_plan(result.intent)
    print(f"intent={result.intent.value}")
    print(f"source={result.source.value}")
    print(
        "plan="
        f"profile:{plan.use_profile},history:{plan.use_history},"
        f"rag:{plan.use_rag},recommendation:{plan.recommendation}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
