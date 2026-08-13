# AI Router·RAG 구조와 점검 가이드

이 문서는 Fit-PT AI 코치의 현재 실행 구조와 로컬 개발 환경에서 RAG 동작을 확인하는 방법을 설명합니다.

## 현재 실행 구조

```text
POST /chat
  → QuestionRouter
      → 확실한 질문: Rule fast path
      → 그 외 질문: LLM 의미 분류 + Pydantic 검증
  → RoutePlan
      → 필요한 사용자 SQL context만 조회
      → 필요한 경우에만 Supabase pgvector RAG 검색
  → LangChain ChatPromptTemplate
  → 기존 OpenAI 또는 Claude provider
  → 추천 응답 Pydantic 검증
  → FastAPI 응답
```

Router는 Intent만 결정하고 SQL이나 RAG를 직접 실행하지 않습니다. 인증된 `user_id`가 필요한 사용자 데이터 조회는 서버의 orchestration 계층에서 수행합니다.

| Intent | Profile | 운동 기록 SQL | RAG | 추천 카드 |
| --- | --- | --- | --- | --- |
| `CHAT` | X | X | X | X |
| `WORKOUT_HISTORY` | X | O | X | X |
| `FITNESS_KNOWLEDGE` | X | X | O | X |
| `PERSONAL_COACHING` | O | O | O | X |
| `ROUTINE_RECOMMENDATION` | O | O | O | O |

주요 구현 경로:

- `apps/api/app/services/ai/question_router.py`: Intent 분류와 RoutePlan
- `apps/api/app/services/ai/orchestrator.py`: SQL·RAG 선택 실행과 provider 호출
- `apps/api/app/services/context.py`: 인증 사용자 운동 context
- `apps/api/app/services/rag/retriever.py`: 질문 embedding과 pgvector 검색
- `apps/api/app/services/ai/prompts.py`: LangChain 의도별 PromptTemplate
- `apps/api/app/services/ai/recommendation_schema.py`: 추천 카드 스키마

## 1. 설정 확인

`apps/api`에서 실행합니다.

```powershell
python -c "from app.core.config import settings; print(settings.OPENAI_EMBEDDING_MODEL, settings.EMBEDDING_DIMENSIONS, settings.RAG_TOP_K, settings.RAG_MATCH_THRESHOLD)"
```

API 키 자체는 출력하거나 공유하지 않습니다. `.env`의 임계값을 변경했다면 FastAPI 서버를 재시작해야 합니다.

## 2. 적재 상태 확인

Supabase SQL Editor에서 읽기 전용으로 확인합니다.

```sql
select
  kd.id,
  kd.title,
  kd.source_name,
  kd.language,
  count(kc.id) as chunk_count
from knowledge_documents kd
left join knowledge_chunks kc on kc.document_id = kd.id
group by kd.id
order by kd.created_at desc;
```

문서가 있지만 `chunk_count=0`이면 적재가 완료되지 않은 상태입니다.

## 3. Router 확인

```powershell
python scripts\route_question.py "근성장에 적절한 반복 수는?"
```

운동 전문지식 질문의 정상 예:

```text
intent=FITNESS_KNOWLEDGE
source=llm
plan=profile:False,history:False,rag:True,recommendation:False
```

`source=rule`과 `source=llm`은 모두 정상입니다. 중요한 값은 질문에 맞는 `intent`와 `rag:True`입니다. `source=fallback`, `intent=CHAT`이면 LLM Router 오류 로그를 확인합니다.

## 4. Retriever 확인

Windows 콘솔에서는 문서의 특수문자 출력 오류를 피하기 위해 `-X utf8`을 사용합니다.

먼저 임계값 없이 상위 결과와 실제 점수를 확인합니다.

```powershell
python -X utf8 scripts\search_knowledge.py `
  "40%, 60%, 80% 1RM 중 어떤 강도가 호르몬 반응이 좋아?" `
  --threshold 0
```

그다음 현재 운영 임계값으로 실행합니다.

```powershell
python -X utf8 scripts\search_knowledge.py `
  "40%, 60%, 80% 1RM 중 어떤 강도가 호르몬 반응이 좋아?"
```

판단 방법:

- 관련 청크가 상위에 있고 운영 임계값을 넘음: Retriever 정상
- `--threshold 0`에서는 관련 청크가 나오지만 기본 실행에서는 없음: 임계값 보정 필요
- 상위 결과가 다른 주제임: 문서 정제, 청킹 또는 검색 질의 개선 필요
- 관련 없는 질문도 운영 임계값을 넘음: 임계값이 너무 낮을 가능성

임계값은 질문 하나가 아니라 관련 질문과 무관 질문을 함께 평가해 결정합니다.

## 5. 웹의 최종 답변 확인

서버를 재시작합니다.

```powershell
python -m uvicorn app.main:app --reload
```

웹에서 다음 유형을 확인합니다.

| 질문 | 기대 결과 |
| --- | --- |
| `안녕` | 일반 대화, SQL/RAG 사용 안 함 |
| `최근 벤치 중량 알려줘` | 인증 사용자의 SQL 기록만 사용 |
| `근성장에 적절한 반복 수는?` | RAG 지식 답변, 추천 카드 없음 |
| `40%, 60%, 80% 1RM 중 어떤 강도가 호르몬 반응이 좋아?` | 관련 학술 자료 근거와 `[자료 N]` 표시 |
| `내 최근 벤치 기록을 보면 중량을 올려도 될까?` | Profile + SQL + RAG 기반 코칭 |
| `최근 기록 기준으로 오늘 가슴 루틴 추천해줘` | Profile + SQL + RAG 및 추천 카드 |

현재 공개 `/chat` 응답은 내부 `intent`, `rag_status`, 유사도 점수를 노출하지 않습니다. 따라서 다음 세 조건을 함께 확인해야 합니다.

1. Router CLI에서 `rag:True`
2. 검색 CLI에서 운영 임계값 이상의 관련 청크
3. 웹 답변에서 문서 고유 내용과 `[자료 N]` 인용

`rag:True`는 검색 시도를 의미하며 문서를 찾았다는 뜻은 아닙니다. 검색 결과가 없으면 orchestrator의 상태는 `empty`, Vector DB 호출이 실패하면 `unavailable`이 되고, 둘 다 검색 자료를 인용하지 않도록 프롬프트에 전달됩니다.

## 6. 자동화 테스트

외부 OpenAI·Claude·Supabase 호출은 mock하고 Router부터 추천 검증까지 실행합니다.

```powershell
python -m unittest discover -s tests -v
```

RAG 통합 흐름만 실행하려면 다음 명령을 사용합니다.

```powershell
python -m unittest tests.test_ai_rag_integration -v
```

자동화 테스트는 코드 연결과 계약을 검증합니다. 실제 embedding 검색 품질은 적재 문서와 Supabase 데이터에 따라 달라지므로 검색 CLI와 웹 질문으로 별도 확인해야 합니다.

## 자주 발생하는 문제

### Router는 `rag:True`인데 답변에 출처가 없음

검색 CLI에서 운영 임계값 이상의 결과가 있는지 확인합니다. 결과가 없다면 LLM 일반 지식으로 답할 수 있지만 검색 자료를 인용해서는 안 됩니다.

### 검색 CLI에서는 나오지만 웹에서는 이전 동작을 보임

`.env` 또는 Python 코드를 변경한 뒤 FastAPI 프로세스가 재시작됐는지 확인합니다.

### 한국어 질문에서 영어 원문 검색 점수가 낮음

질문과 같은 언어로 작성한 승인된 요약문을 별도 문서로 적재하는 방법을 우선 고려합니다. 임계값을 과도하게 낮추면 무관한 청크가 포함될 수 있습니다.

### 추천 카드가 표시되지 않음

루틴 질문이 `ROUTINE_RECOMMENDATION`인지 확인합니다. 추천 데이터가 필수 필드, 최대 8개 웨이트 종목, 러닝 페이스 형식 등 Pydantic 검증을 통과하지 못하면 텍스트만 반환됩니다.
