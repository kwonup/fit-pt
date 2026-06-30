# CLAUDE.md — 핏피티 (Fit PT)

AI 코딩 도구가 이 프로젝트를 이해하고 일관성 있게 코드를 작성하기 위한 규칙과 가이드.

## 프로젝트 개요

핏피티는 AI 챗봇 기반 운동 기록 및 루틴 추천 웹앱이다.

**핵심 흐름:**
운동 기록(웨이트/러닝/기타) → AI 챗봇 추천 요청 → 추천 카드 생성 → "운동반영하기" 클릭 → 기록 폼 자동 채우기 → 저장

**핵심 차별점:** AI 추천 결과를 텍스트로 끝내지 않고, 실제 운동 기록 데이터로 전환하는 것.

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12 |
| Database / Auth | Supabase (PostgreSQL + Supabase Auth) |
| Frontend 배포 | Vercel (Root: apps/web) |
| Backend 배포 | Render (Root: apps/api) |

## 폴더 구조

```
apps/web/
  app/            # Next.js App Router (페이지, 레이아웃)
  components/     # 재사용 UI 컴포넌트
  components/ui/  # shadcn/ui 기반 공통 UI 컴포넌트
  lib/            # API 클라이언트, 유틸리티, Supabase 설정
  types/          # TypeScript 타입 정의

apps/api/
  app/
    routers/      # 엔드포인트 그룹 (profile, workouts, chat, stats)
    models/       # Pydantic 모델
    schemas/      # Pydantic 스키마 (요청/응답 DTO)
    services/     # 비즈니스 로직
      ai/         # AI provider 추상화 (factory, openai/claude, prompts, parser)
      context.py  # 프로필 + 최근 기록 컨텍스트 구성
    core/         # 설정(config.py), 인증 의존성(deps.py)

supabase/
  migrations/     # 순서대로 실행되는 SQL 마이그레이션
  seed.sql        # 개발용 초기 데이터
```

## 코드 작성 기준

### 공통

- 불필요한 주석 작성 금지. WHY가 명확할 때만 한 줄 주석 허용
- 환경변수는 반드시 .env 파일에서 관리. 코드에 하드코딩 절대 금지
- 기능을 과하게 선구현하지 않는다. MVP 범위만 구현
- 사용자가 직접 커밋하므로, 한 번에 너무 많은 기능을 구현하지 않는다.
- 구현은 커밋하기 좋은 작은 단위로 나눈다. 예: "인증 UI", "프로필 API", "운동 기록 생성 API"처럼 하나의 목적이 명확한 범위로 작업한다.
- 작업을 마칠 때는 변경 요약과 함께 추천 커밋 메시지를 반드시 제안한다.
- 커밋 메시지는 가능하면 Conventional Commits 형식을 따른다. 예: `feat: 초기 프로젝트 구조 설정`, `fix: 운동 기록 생성 검증 수정`, `docs: API 명세 보완`

### Frontend (Next.js)

- **App Router 사용**. Pages Router 사용 금지
- **서버 컴포넌트 우선**. 클라이언트 상태가 필요한 경우에만 `'use client'` 추가
- **API 호출은 apps/api FastAPI 서버로만 한다.** Supabase DB를 프론트에서 직접 쿼리하지 않는다
  - 예외: Supabase Auth는 프론트에서 직접 사용 가능 (`@supabase/ssr` 활용)
- TypeScript 타입은 `types/` 폴더에 분리 정의
- **Tailwind CSS만 사용한다.** CSS 모듈, styled-components, inline style 사용 금지
- **shadcn/ui는 "선별 도입" 한다.** 기존 화면(온보딩/대시보드/캘린더/기록 등)은 순수 Tailwind를 유지하고, 전면 전환하지 않는다.
- **새 화면이나 복합 컴포넌트**(챗봇, 다이얼로그, 탭 등 직접 구현이 번거로운 것)에 한해 `components/ui/`의 shadcn 컴포넌트를 사용한다. 단순 버튼/입력은 raw Tailwind로 충분하면 그대로 둔다.
- shadcn/ui 컴포넌트는 필요한 것만 추가한다. 한 번에 많은 컴포넌트를 설치하지 말고, 구현할 화면에 필요한 단위로 추가한다.
- shadcn/ui 설정은 `apps/web/components.json`, 공통 유틸은 `apps/web/lib/utils.ts`, 디자인 토큰은 `apps/web/app/globals.css`와 `apps/web/tailwind.config.ts`를 기준으로 한다.
- 아이콘이 필요한 버튼/액션에는 가능하면 `lucide-react` 아이콘을 사용한다.

### Backend (FastAPI)

- **모든 엔드포인트에 인증 의존성(`get_current_user_id`)을 적용한다.** `/health` 제외
- **사용자 데이터 조회 시 반드시 `user_id`로 필터링한다.** 타인 데이터 접근 불가
- **AI 추천 응답은 반드시 구조화된 JSON(`structured_data`)으로 파싱하여 저장한다.**
  - 이것이 "운동반영하기" 기능의 입력값이다. 파싱 실패 시 운동반영하기가 동작하지 않는다
- **AI 엔진은 provider 추상화로 분리한다** (`app/services/ai/`). `AI_PROVIDER` 환경변수로 `openai`/`claude`를 선택하며, 라우터는 provider 구현을 직접 알지 않는다.
- AI 추천 컨텍스트는 RAG가 아니라 **정형 운동 기록 기반 동적 SQL 컨텍스트 주입**을 우선한다.
  - 사용자 메시지에 "지난번", "2주 전", "최고기록", 특정 부위/종목 키워드가 있으면 관련 운동 세트 상세를 SQL로 조회해 프롬프트에 추가한다.
  - 운동 기록처럼 날짜/중량/반복수가 명확한 데이터는 벡터 검색보다 SQL 조회가 더 정확하고 비용이 낮다.
- Supabase 클라이언트는 `service_role_key`로 초기화한다 (RLS 우회 목적)
- 라우터는 역할별로 분리한다: `routers/profile.py`, `routers/workouts.py`, `routers/chat.py`, `routers/stats.py`

### 보안 (절대 위반 금지)

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: **백엔드에서만** 사용
- `SUPABASE_SERVICE_ROLE_KEY`: **백엔드에서만** 사용
- 프론트엔드에서 사용 가능한 환경변수: `NEXT_PUBLIC_` 접두사가 붙은 것만
- `.env.example`에는 **실제 키를 절대 넣지 않는다** (git에 커밋되는 템플릿). 실제 값은 `.env`/`.env.local`에만 둔다.

## 구현 우선순위

> 상세 진행 상황은 `docs/project-plan.md`를 기준으로 하며, 아래는 요약이다.

### Phase 1 — 기반 세팅 ✅
- [x] 모노레포 구조 생성
- [x] DB 스키마 설계 (supabase/migrations/)
- [x] Supabase 프로젝트 연결 (002·003 마이그레이션은 SQL Editor에서 실행 필요)
- [x] Next.js 기본 라우팅 구성
- [x] FastAPI 기본 서버 구동 확인

### Phase 2 — 인증 & 프로필 ✅
- [x] Supabase Auth 연동 (이메일 로그인/가입)
- [x] 로그인 / 회원가입 UI (`/login`)
- [x] 프로필 설정(온보딩) 페이지 (목표, 숙련도, 페르소나)
- [x] FastAPI 인증 미들웨어 (`app/core/deps.py`)

### Phase 3 — 운동 기록 CRUD ✅
- [x] 웨이트 / 러닝 / 기타 기록 작성 UI (`/workouts/new`)
- [x] 운동 기록 조회 / 삭제 (상세 `/workouts/[id]`)
- [x] 월간 캘린더 (웨이트/러닝/기타 색상 구분, `/calendar`)

### Phase 4 — AI 챗봇 (진행 중)
- [x] FastAPI `/chat` 엔드포인트
- [x] AI provider 연동 (OpenAI/Claude, 기록 + 프로필 컨텍스트)
- [x] 페르소나별 말투 적용 (angel / tiger)
- [ ] 챗봇 UI + 추천 카드 (웨이트 / 러닝 / 기타)

### Phase 5 — 운동반영하기 (핵심 차별점)
- [x] AI `structured_data` JSON 파싱 및 저장 (백엔드 완료)
- [ ] "운동반영하기" 버튼
- [ ] `structured_data` → 기록 폼 초기값 매핑
- [ ] 저장 후 캘린더 & 마이페이지 즉시 반영

### Phase 6 — 마이페이지 & 완성도
- [ ] 주당 운동 시간 바 차트 (4주/8주) — 백엔드 `/stats/weekly` 완료
- [ ] 요약 카드 (이번 주 시간, 총 횟수, 최근 운동일) — 백엔드 `/stats/summary` 완료
- [ ] 반응형 모바일 최적화

## AI 추천 structured_data 형식

"운동반영하기"를 위한 핵심 데이터 구조. FastAPI가 AI provider(OpenAI/Claude) 응답을 이 형식으로 파싱해서 저장해야 한다.
`type`은 `weight`, `running`, `other` 중 하나이며, `workout_type`과 동일해야 한다.
모든 타입의 `title`은 실제 운동 기록 생성 API의 공통 필수 필드로 매핑된다.

### 웨이트트레이닝

```json
{
  "type": "weight",
  "title": "오늘의 등 루틴",
  "estimated_duration_minutes": 50,
  "muscle_group": "등",
  "exercises": [
    {
      "name": "랫풀다운",
      "sets": [
        { "set_number": 1, "reps": 12, "weight_kg": 40, "rest_seconds": 90 }
      ],
      "notes": "허리 중립 유지"
    }
  ],
  "cautions": "허리 주의로 데드리프트 제외"
}
```

**기록 API 매핑**
- `title` → `/workouts/weight.title`
- `estimated_duration_minutes` → `/workouts/weight.duration_minutes`
- `exercises[].name` → `/workouts/weight.exercises[].exercise_name`
- `exercises[].sets[].rest_seconds`는 추천 카드 표시용이며, 현재 `weight_sets`에는 저장하지 않는다.
- `muscle_group`은 AI 추천/표시용 예약 필드이며, 현재 웨이트 기록 생성 API에는 보내지 않는다.

### 러닝

```json
{
  "type": "running",
  "title": "오늘의 러닝 루틴",
  "total_duration_minutes": 40,
  "distance_km": 5.0,
  "avg_pace": "8:00",
  "warmup": "5분 빠른 걷기",
  "main": "30분 페이스 유지 러닝",
  "cooldown": "5분 스트레칭",
  "cautions": ""
}
```

**기록 API 매핑**
- `title` → `/workouts/running.title`
- `total_duration_minutes` → `/workouts/running.duration_minutes`
- `distance_km` → `/workouts/running.distance_km`
- `avg_pace` → `/workouts/running.avg_pace`
- `warmup`, `main`, `cooldown`, `cautions`는 추천 카드 표시용이며, 현재 러닝 상세 테이블에는 별도 저장하지 않는다.

### 기타

```json
{
  "type": "other",
  "title": "오늘의 회복 스트레칭",
  "content": "허리 부담을 줄이기 위해 고관절 가동성 10분, 햄스트링 스트레칭 10분, 코어 안정화 운동 10분을 진행하세요.",
  "estimated_duration_minutes": 30,
  "cautions": "통증이 생기면 즉시 중단하고 강도를 낮추세요."
}
```

**기록 API 매핑**
- `title` → `/workouts/other.title`
- `content` → `/workouts/other.content`
- `estimated_duration_minutes` → `/workouts/other.duration_minutes`
- `cautions`는 추천 카드 표시용이며, 현재 `other_sessions`에는 저장하지 않는다.

## MVP 범위 외 기능 (구현 금지)

- 소셜 기능 (팔로우, 공유, 랭킹)
- 유료 결제 / 구독
- 웨어러블 데이터 연동
- 영양 / 식단 관리
- 네이티브 모바일 앱
- Kakao / Naver OAuth (v2)
