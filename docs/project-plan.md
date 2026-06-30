# 프로젝트 플랜 — 핏피티 (Fit PT)

PRD 기반 개발 계획서. 구현 단계별 체크리스트.

## 서비스 한 줄 요약

AI 챗봇으로 운동 추천을 받고, "운동반영하기" 버튼 하나로 추천 결과를 실제 운동 기록으로 저장하는 웹앱.

## 기술 스택

| 영역 | 기술 | 배포 |
|---|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui | Vercel (Root: apps/web) |
| Backend | FastAPI, Python 3.12 | Render (Root: apps/api) |
| DB / Auth | Supabase (PostgreSQL + Auth) | Supabase Cloud |

## 핵심 데이터 흐름 (운동반영하기)

```
사용자 → 챗봇 입력
    ↓
FastAPI: 프로필 + 최근 30일 기록 → OpenAI API
    ↓
OpenAI: structured_data (JSON) 반환
    ↓
FastAPI: ai_recommendations 테이블 저장
    ↓
Next.js: 추천 카드 렌더링 + "운동반영하기" 버튼
    ↓
사용자 클릭 → structured_data → 기록 폼 초기값
    ↓
사용자 수정 후 저장 → workout_sessions 테이블
    ↓
캘린더 & 마이페이지 즉시 반영
```

## 개발 단계

### Phase 1 — 기반 세팅 ✅
- [x] 모노레포 폴더 구조 생성
- [x] DB 스키마 설계 및 마이그레이션 파일 작성
- [x] Next.js 기본 구조 (App Router, Tailwind)
- [x] shadcn/ui 초기 설정 및 기본 컴포넌트 추가
- [x] FastAPI 기본 서버 (라우터 구조, 인증 미들웨어)
- [x] 문서 초안 (README, CLAUDE.md, docs/)
- [x] Pydantic 요청 스키마 1차 정리
- [x] GitHub remote 연결 (`https://github.com/kwonup/fit-pt.git`)
- [ ] Supabase 프로젝트 연결 및 마이그레이션 실행
- [ ] 로컬 서버 구동 확인 (web: 3000, api: 8000)

### Phase 2 — 인증 & 프로필
- [x] Supabase Auth 이메일 로그인/가입 구현 (`@supabase/ssr` 브라우저/서버 클라이언트 + 미들웨어 세션 갱신)
- [x] 로그인 / 회원가입 페이지 UI (`/login`)
- [x] 로그인 후 프로필 미설정 시 온보딩 리다이렉트 (`/dashboard`에서 `GET /profile` 404 → `/onboarding`)
- [x] 프로필 설정 페이지 (목표, 숙련도, 주 운동 타입, 빈도, 주의 부위, 페르소나) → `PUT /profile`
- [x] 라우트 보호 미들웨어 (`middleware.ts`: 미로그인 시 `/login` 리다이렉트)
- [ ] FastAPI 인증 토큰 검증 통합 테스트 (실제 Supabase 연결 후)

### Phase 3 — 운동 기록 CRUD
- [x] 웨이트트레이닝 기록 작성 UI (종목 추가, 세트/중량/반복 입력) — `/workouts/new`
- [x] 러닝 기록 작성 UI (거리/시간 입력 → 페이스 자동 계산) — `/workouts/new`
- [x] FastAPI /workouts/weight POST 1차 구현
- [x] FastAPI /workouts/running POST 1차 구현
- [x] 운동 기록 상세 조회 / 공통 필드 수정 / 삭제 1차 구현
- [x] 월간 캘린더 (웨이트/러닝/기타 색상 구분) — `/calendar`
- [x] 날짜 클릭 → 해당 날짜 기록 목록 → 상세 이동 (`/workouts/[id]`)
- [x] 기록 상세 화면 (타입별 렌더링) + 삭제

### Phase 4 — AI 챗봇
- [ ] FastAPI /chat POST 구현
  - [ ] 사용자 프로필 조회
  - [ ] 최근 30일 운동 기록 요약
  - [ ] OpenAI API 호출 (structured output)
  - [ ] ai_recommendations 저장
  - [ ] chat_messages 저장
- [ ] 챗봇 UI (채팅창, 메시지 렌더링)
- [ ] 웨이트 추천 카드 컴포넌트
- [ ] 러닝 추천 카드 컴포넌트
- [ ] 페르소나별 말투 적용 (angel/tiger 시스템 프롬프트)

### Phase 5 — 운동반영하기
- [ ] structured_data → 기록 폼 초기값 매핑 로직
- [ ] "운동반영하기" 버튼 동작
- [ ] 폼 진입 시 추천 데이터 pre-fill
- [ ] 저장 후 캘린더 & 마이페이지 즉시 반영 확인

### Phase 6 — 마이페이지 & 완성도
- [ ] FastAPI /stats/weekly, /stats/summary 구현
- [ ] 주당 운동 시간 바 차트 (4주/8주)
- [ ] 요약 카드 (이번 주 시간, 총 횟수, 최근 운동일)
- [ ] 반응형 모바일 레이아웃

## 주요 파일 위치

| 역할 | 파일 경로 |
|---|---|
| DB 스키마 | supabase/migrations/001_initial_schema.sql |
| API 명세 | docs/api-spec.md |
| DB 설계 | docs/db-schema.md |
| AI 규칙 | CLAUDE.md |
| 타입 정의 | apps/web/types/index.ts |
| API 클라이언트 | apps/web/lib/api.ts |
| Supabase 클라이언트 | apps/web/lib/supabase.ts |
| shadcn/ui 설정 | apps/web/components.json |
| shadcn/ui 컴포넌트 | apps/web/components/ui/ |
| UI 유틸리티 | apps/web/lib/utils.ts |
| FastAPI 진입점 | apps/api/app/main.py |
| 인증 의존성 | apps/api/app/core/deps.py |
