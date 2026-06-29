# DB 스키마 설계 — 핏피티 (Fit PT)

- **DB:** Supabase (PostgreSQL)
- **인증:** Supabase Auth (`auth.users` 기본 제공)
- **보안:** 모든 테이블에 Row Level Security (RLS) 적용
- **마이그레이션 파일:** `supabase/migrations/001_initial_schema.sql`

## ERD 개요

```
auth.users (Supabase 기본)
  ├── user_profiles       (1:1)
  ├── workout_sessions    (1:N)
  │     ├── weight_exercises  (1:N, workout_type='weight' 세션만)
  │     │     └── weight_sets (1:N)
  │     └── running_sessions  (1:1, workout_type='running' 세션만)
  ├── ai_recommendations  (1:N)
  └── chat_messages       (1:N)

workout_sessions.ai_recommendation_id → ai_recommendations (운동반영하기로 생성 시)
chat_messages.recommendation_id       → ai_recommendations (추천 메시지와 연결)
```

## 테이블 정의

### user_profiles

사용자 운동 프로필. AI 추천의 핵심 컨텍스트.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | auth.users.id 참조 | |
| fitness_goals | TEXT[] | DEFAULT '{}' | 복수 선택 (체중 감량 등) |
| fitness_level | TEXT | CHECK (초보/중급/고급) | 숙련도 |
| main_workout_type | TEXT | CHECK (웨이트트레이닝/러닝/둘다) | 주 운동 타입 |
| weekly_frequency | INT | CHECK (1-7) | 주당 운동 가능 횟수 |
| caution_areas | TEXT[] | DEFAULT '{}' | 주의/부상 부위 |
| persona | TEXT | CHECK (angel/tiger), DEFAULT 'angel' | 트레이너 페르소나 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 트리거로 자동 갱신 |

### workout_sessions

운동 세션의 공통 정보. 웨이트와 러닝 공용.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | uuid_generate_v4() | |
| user_id | UUID | auth.users 참조, NOT NULL | |
| workout_date | DATE | NOT NULL | 운동 날짜 |
| workout_type | TEXT | CHECK (weight/running), NOT NULL | 운동 타입 |
| duration_minutes | INT | | 총 운동 시간(분) |
| memo | TEXT | | 메모 |
| ai_recommendation_id | UUID | ai_recommendations 참조, nullable | 운동반영하기로 생성 시 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | 트리거로 자동 갱신 |

### weight_exercises

웨이트 세션의 운동 종목. Session 하나에 여러 종목.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | | |
| session_id | UUID | workout_sessions 참조 | |
| muscle_group | TEXT | NOT NULL | 가슴/등/어깨/팔/하체/코어/전신 |
| exercise_name | TEXT | NOT NULL | 운동 종목명 |
| order_index | INT | DEFAULT 0 | 순서 |

### weight_sets

운동 종목의 세트별 데이터. Exercise 하나에 여러 세트.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | | |
| exercise_id | UUID | weight_exercises 참조 | |
| set_number | INT | NOT NULL | 세트 번호 |
| weight_kg | NUMERIC(5,2) | | 중량(kg) |
| reps | INT | | 반복 수 |

### running_sessions

러닝 세션 상세. workout_sessions와 1:1.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | | |
| session_id | UUID | UNIQUE, workout_sessions 참조 | |
| distance_km | NUMERIC(5,2) | | 거리(km) |
| duration_minutes | INT | | 소요 시간(분) |
| avg_pace | TEXT | | 평균 페이스 "mm:ss" 형식 |
| intensity | TEXT | CHECK (낮음/보통/높음) | 강도 |

### ai_recommendations

AI 추천 이력. **structured_data가 "운동반영하기"의 입력값.**

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | | |
| user_id | UUID | auth.users 참조 | |
| user_message | TEXT | NOT NULL | 사용자 요청 메시지 |
| ai_response_text | TEXT | NOT NULL | AI 응답 텍스트 (UI 표시용) |
| structured_data | JSONB | | 구조화된 루틴 (운동반영하기 입력값) |
| workout_type | TEXT | CHECK (weight/running) | |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

### chat_messages

채팅 대화 이력.

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| id | UUID (PK) | | |
| user_id | UUID | auth.users 참조 | |
| role | TEXT | CHECK (user/assistant) | 발화자 |
| content | TEXT | NOT NULL | 메시지 내용 |
| recommendation_id | UUID | ai_recommendations 참조, nullable | 추천 카드 연결 |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

---

## AI structured_data JSON 구조

`ai_recommendations.structured_data` 컬럼의 형식.
이 구조가 프론트엔드 기록 폼의 초기값으로 매핑됩니다.

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
        { "set_number": 1, "reps": 12, "weight_kg": 40, "rest_seconds": 90 },
        { "set_number": 2, "reps": 10, "weight_kg": 45, "rest_seconds": 90 }
      ],
      "notes": "허리 중립 유지"
    }
  ],
  "cautions": "허리 주의로 데드리프트 제외"
}
```

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

---

## RLS 정책 요약

| 테이블 | 정책 |
|---|---|
| user_profiles | `id = auth.uid()` + `WITH CHECK` |
| workout_sessions | `user_id = auth.uid()` + `WITH CHECK` |
| weight_exercises | 본인 session의 exercises만 |
| weight_sets | 본인 exercise의 sets만 |
| running_sessions | 본인 session만 |
| ai_recommendations | `user_id = auth.uid()` + `WITH CHECK` |
| chat_messages | `user_id = auth.uid()` + `WITH CHECK` |

> FastAPI는 `service_role_key`로 Supabase에 접근하므로 RLS를 우회합니다.
> 대신 **모든 쿼리에서 `user_id = {current_user_id}` 필터를 코드 레벨에서 적용**해야 합니다.

## 인덱스

캘린더, 통계, 채팅 이력 조회를 위해 아래 인덱스를 둡니다.

| 인덱스 | 목적 |
|---|---|
| `idx_workout_sessions_user_date` | 사용자별 월간 운동 기록, 주간 통계 조회 |
| `idx_ai_recommendations_user_created_at` | 사용자별 AI 추천 이력 최신순 조회 |
| `idx_chat_messages_user_created_at` | 사용자별 채팅 이력 시간순 조회 |
| `idx_weight_exercises_session_order` | 웨이트 상세의 종목 순서 조회 |
| `idx_weight_sets_exercise_set_number` | 웨이트 상세의 세트 순서 조회 |
