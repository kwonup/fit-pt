# 핏피티 (Fit PT)

AI 챗봇이 운동 기록을 분석하고 맞춤 루틴을 추천하는 웹 서비스.
추천 결과를 **"운동반영하기"** 버튼 하나로 실제 운동 기록으로 전환하는 것이 핵심 기능입니다.

## 주요 기능

- AI 챗봇으로 자연어 운동 추천 요청 ("오늘 등 운동 50분 루틴 짜줘")
- 추천 루틴을 즉시 운동 기록으로 반영 (**운동반영하기**)
- 웨이트트레이닝 / 러닝 기록 CRUD
- 월간 캘린더로 운동 패턴 확인 (웨이트 / 러닝 구분 표시)
- 마이페이지에서 주당 운동 시간 그래프
- 두 가지 트레이너 페르소나 선택 (상냥한 천사 코치 / 엄격한 호랑이 코치)

## 기술 스택

| 영역 | 기술 | 배포 |
|---|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS | Vercel |
| Backend | FastAPI, Python 3.12 | Render |
| Database / Auth | Supabase (PostgreSQL + Auth) | Supabase Cloud |

## 프로젝트 구조

```
fit-pt/
  apps/
    web/    # Next.js + TypeScript (Vercel 배포, Root Directory: apps/web)
    api/    # FastAPI (Render 배포, Root Directory: apps/api)
  supabase/ # DB 마이그레이션 & 시드 데이터
  docs/     # 기획서, API 명세, DB 설계
```

## 실행 방법

### 사전 요구사항

- Node.js 20+
- Python 3.12+
- Supabase 계정 및 프로젝트 생성

### 환경변수 설정

```bash
# 프론트엔드
cp apps/web/.env.local.example apps/web/.env.local
# apps/web/.env.local에 Supabase URL, Anon Key, API URL 입력

# 백엔드
cp apps/api/.env.example apps/api/.env
# apps/api/.env에 Supabase 키, OpenAI API 키 입력
```

### 프론트엔드 실행

```bash
cd apps/web
npm install
npm run dev
# http://localhost:3000
```

### 백엔드 실행

```bash
cd apps/api
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
# source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# http://localhost:8000
# API 문서: http://localhost:8000/docs
```

### Supabase 마이그레이션

```bash
# Supabase CLI 설치 후
supabase db push
# 또는 Supabase 대시보드 SQL Editor에서 supabase/migrations/ 파일 직접 실행
```

## 배포

| 환경 | URL |
|---|---|
| Frontend (Vercel) | 추가 예정 |
| Backend API (Render) | 추가 예정 |
| GitHub | https://github.com/kwonup/fit-pt.git |

> Vercel 배포 시 Root Directory: `apps/web`
> Render 배포 시 Root Directory: `apps/api`

## 데모 시나리오

1. 회원가입 후 프로필 설정 (목표, 숙련도, 트레이너 페르소나)
2. AI 챗봇에 "오늘 등 운동 50분 루틴 짜줘. 허리가 조금 불편해서 데드리프트는 빼줘" 입력
3. AI 추천 카드 확인 → **"운동반영하기"** 버튼 클릭
4. 추천 내용이 채워진 기록 폼을 수정 후 저장
5. 캘린더에서 오늘 운동 기록 확인
6. 마이페이지에서 주간 운동 시간 그래프 확인
