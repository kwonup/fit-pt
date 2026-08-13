# 프로젝트 구현 현황 — 핏피티 (Fit-PT)

현재 코드와 마이그레이션을 기준으로 정리한 구현 현황 및 후속 계획입니다.

## 서비스 한 줄 요약

운동 기록과 검증된 전문지식을 바탕으로 AI 코칭을 제공하고, 구조화된 추천을 실제 운동 기록으로 전환하는 개인화 운동 관리 웹앱입니다.

## 기술 스택

| 영역 | 기술 | 상태 |
| --- | --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui | 구현 |
| Backend | FastAPI 0.115, Python 3.12, Pydantic | 구현 |
| DB / Auth | Supabase PostgreSQL, Auth, RLS | 구현 |
| AI | OpenAI 또는 Claude provider | 구현 |
| RAG | LangChain, OpenAI Embeddings, Supabase pgvector | 구현 |
| 배포 | Vercel / Render 목표 | 설정·URL 미구성 |

## 현재 핵심 흐름

```text
사용자 질문
  → Question Router (Rule fast path → 애매하면 LLM 의미 분류)
  → RoutePlan
      CHAT                  → LLM
      WORKOUT_HISTORY       → 사용자 SQL
      FITNESS_KNOWLEDGE     → 공용 지식 RAG
      PERSONAL_COACHING     → Profile + 사용자 SQL + RAG
      ROUTINE_RECOMMENDATION→ Profile + 사용자 SQL + RAG + 추천 JSON
  → LangChain 의도별 PromptTemplate
  → OpenAI 또는 Claude
  → Pydantic 추천 스키마 검증
  → FastAPI 응답
  → 추천 카드 → 기록 폼 → workout_sessions 저장
```

사용자 운동 날짜·중량·반복·거리 같은 정형 데이터는 SQL로 조회합니다. 논문·가이드라인 같은 공용 비정형 지식만 pgvector RAG로 검색하며 사용자 개인 데이터는 지식 저장소에 넣지 않습니다.

## 완료된 단계

### Phase 1 — 기반·DB ✅

- [x] `apps/web`, `apps/api` 모노레포 구성
- [x] FastAPI 라우터 및 Next.js App Router 구성
- [x] Supabase Auth·관계형 운동 스키마·RLS
- [x] `001`~`007` 순차 마이그레이션
- [x] 프로필, 운동 기록, 추천, 통계, RAG 테이블과 RPC
- [x] 환경변수 템플릿과 로컬 실행 문서

### Phase 2 — 인증·프로필 ✅

- [x] 이메일 회원가입·로그인
- [x] Supabase SSR 세션 갱신 및 보호 경로 처리
- [x] 프로필 미설정 사용자 온보딩 이동
- [x] 목표, 숙련도, 주 운동 타입, 빈도, 주의 부위, AI persona 저장
- [x] FastAPI Bearer 토큰 검증

### Phase 3 — 운동 기록·통계 ✅

- [x] 웨이트·러닝·기타 기록 생성
- [x] 전체/월별 목록과 타입별 상세 조회
- [x] 공통 필드 수정 및 기록 삭제
- [x] 월간 캘린더
- [x] 이번 주 시간·전체 횟수·최근 운동일 요약
- [x] 4주/8주 운동 시간·웨이트 볼륨·러닝 거리 집계

### Phase 4 — AI 챗봇·추천 전환 ✅

- [x] OpenAI/Claude provider 추상화
- [x] 페르소나별 말투
- [x] 최근 30일 요약과 질문별 상세 SQL context
- [x] 최근 작업 중량·역대 최고 중량 RPC
- [x] 웨이트·러닝·기타 Pydantic 추천 스키마
- [x] 챗봇 UI 및 운동 타입별 추천 카드
- [x] `sessionStorage` 기반 기록 폼 자동 채움
- [x] `ai_recommendation_id`를 실제 운동 기록에 연결

### Phase 5 — Question Router·RAG ✅

- [x] 5개 Intent와 RoutePlan
- [x] 확실한 질문의 Rule fast path
- [x] 애매한 표현의 LLM 의미 분류와 JSON/Pydantic 검증
- [x] PDF·Markdown·텍스트 적재 CLI
- [x] 1,000자/200자 overlap 청킹 및 provenance 보존
- [x] `text-embedding-3-small` 1536차원 embedding
- [x] Supabase cosine similarity Retriever
- [x] Intent별 LangChain `ChatPromptTemplate`
- [x] RAG empty/unavailable graceful fallback
- [x] 검색 자료의 `[자료 N]` 인용 지시

### Phase 6 — 테스트·운영 문서 ✅

- [x] Router rule/LLM/fallback 테스트
- [x] 적재·Retriever·사용자 context 단위 테스트
- [x] 프롬프트·추천 계약 테스트
- [x] Router → SQL/RAG → 응답 통합 테스트
- [x] 전체 Python 테스트 57개
- [x] RAG 적재 및 운영 점검 가이드

## 현재 남은 작업

### 우선순위 높음

- [ ] RAG 관련/무관 질문 평가셋과 검색 품질 지표 자동화
- [ ] `chat_messages` 저장·조회 정책 및 대화 복원 API/UI
- [ ] 웨이트 종목·세트와 러닝 상세 수정 API/UI
- [ ] Provider-native structured output 검토
- [ ] 브라우저 E2E 및 CI 파이프라인

### 운영·완성도

- [ ] 실제 배포 설정과 라이브 URL
- [ ] 서비스 스크린샷·데모 GIF·시연 영상
- [ ] 미래 날짜 운동 기록 정책
- [ ] RAG corpus 증가 시 HNSW 인덱스 성능 측정·도입
- [ ] 지식 문서 YAML frontmatter 파싱과 Markdown 헤딩 metadata 보존

## 주요 파일 위치

| 역할 | 파일 경로 |
| --- | --- |
| FastAPI 진입점 | `apps/api/app/main.py` |
| 인증 의존성 | `apps/api/app/core/deps.py` |
| 질문 Router·RoutePlan | `apps/api/app/services/ai/question_router.py` |
| AI Orchestrator | `apps/api/app/services/ai/orchestrator.py` |
| 사용자 SQL context | `apps/api/app/services/context.py` |
| LangChain PromptTemplate | `apps/api/app/services/ai/prompts.py` |
| 추천 Pydantic 계약 | `apps/api/app/services/ai/recommendation_schema.py` |
| RAG 적재·Retriever | `apps/api/app/services/rag/` |
| 운영 CLI | `apps/api/scripts/` |
| AI·RAG 테스트 | `apps/api/tests/` |
| 프론트 추천 타입 | `apps/web/types/index.ts` |
| 추천 폼 전달 | `apps/web/lib/workout-prefill.ts` |
| DB 마이그레이션 | `supabase/migrations/` |
| API 명세 | `docs/api-spec.md` |
| DB 설계 | `docs/db-schema.md` |
| RAG 운영 가이드 | `docs/ai-rag-operations.md` |
