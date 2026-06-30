# API 명세 — 핏피티 (Fit PT)

## 기본 정보

- **Base URL (로컬):** `http://localhost:8000`
- **Base URL (운영):** `https://[render-domain].onrender.com`
- **인증:** Supabase JWT (Bearer 토큰)
- **Content-Type:** `application/json`
- **API 문서 (자동 생성):** `{BASE_URL}/docs`

## 인증

Supabase 로그인 후 받은 액세스 토큰을 모든 요청 헤더에 포함합니다.

```
Authorization: Bearer {supabase_access_token}
```

FastAPI는 토큰을 검증하고 `user_id`를 추출합니다 (`app/core/deps.py`).

---

## 헬스 체크

### GET /health
서버 상태 확인. 인증 불필요.

**Response**
```json
{ "status": "ok" }
```

---

## 프로필

### GET /profile
현재 사용자 프로필 조회.

**Response**
```json
{
  "fitness_goals": ["근력 향상"],
  "fitness_level": "중급",
  "main_workout_type": "웨이트트레이닝",
  "weekly_frequency": 4,
  "caution_areas": ["허리"],
  "persona": "tiger"
}
```

### PUT /profile
프로필 업데이트. 변경할 필드만 전송.

**Request Body**
```json
{
  "fitness_goals": ["근력 향상", "운동 습관 형성"],
  "fitness_level": "중급",
  "persona": "angel"
}
```

**Response:** 업데이트된 프로필 객체

---

## 운동 기록

### GET /workouts
운동 기록 목록 조회.

**Query Parameters**
| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| year | int | 현재 연도 | 조회 연도 |
| month | int | 현재 월 | 조회 월 |

**Response**
```json
[
  {
    "id": "uuid",
    "workout_date": "2026-06-29",
    "workout_type": "weight",
    "title": "저녁 등 워크아웃",
    "duration_minutes": 60,
    "memo": "",
    "ai_recommendation_id": null,
    "created_at": "2026-06-29T10:00:00Z"
  }
]
```

### GET /workouts/{session_id}
운동 기록 상세 조회. 타입에 따라 exercises 또는 running 데이터 포함.

### POST /workouts/weight
웨이트트레이닝 기록 생성.

**Request Body**
```json
{
  "workout_date": "2026-06-29",
  "title": "저녁 등 워크아웃",
  "duration_minutes": 60,
  "memo": "컨디션 좋음",
  "ai_recommendation_id": null,
  "exercises": [
    {
      "exercise_name": "랫풀다운",
      "order_index": 0,
      "sets": [
        { "set_number": 1, "weight_kg": 40, "reps": 12 },
        { "set_number": 2, "weight_kg": 45, "reps": 10 }
      ]
    }
  ]
}
```

> `title`은 모든 운동 타입 공통 **필수** 필드입니다(생성 시). AI 추천 JSON은 `name`을 사용하고, 실제 기록 생성 API로 보낼 때 `exercise_name`으로 매핑합니다.

**Response:** 생성된 Session 객체 (status 201)

### POST /workouts/running
러닝 기록 생성.

**Request Body**
```json
{
  "workout_date": "2026-06-29",
  "title": "아침 인터벌 러닝",
  "distance_km": 5.0,
  "duration_minutes": 40,
  "avg_pace": "8:00",
  "intensity": "보통",
  "memo": "",
  "ai_recommendation_id": null
}
```

> `avg_pace`를 생략하면 서버가 `duration_minutes / distance_km` 기준으로 자동 계산합니다.

**Response:** 생성된 Session 객체 (status 201)

### POST /workouts/other
기타 운동 기록 생성. 웨이트/러닝에 속하지 않는 운동을 자유 서술로 기록.

**Request Body**
```json
{
  "workout_date": "2026-06-29",
  "title": "주말 클라이밍",
  "content": "실내 클라이밍 1시간, 볼더링 V3 5개 완등",
  "duration_minutes": 60,
  "memo": "",
  "ai_recommendation_id": null
}
```

> `content`는 필수입니다. 별도 `other_sessions` 테이블에 저장됩니다.

**Response:** 생성된 Session 객체 (status 201)

### PUT /workouts/{session_id}
운동 세션의 공통 필드 수정. 본인 기록만 수정 가능.

**현재 MVP 수정 가능 필드**
- `workout_date`
- `title`
- `duration_minutes`
- `memo`

> 웨이트 종목/세트와 러닝 상세 수정은 다음 단계에서 별도 구현합니다.

### DELETE /workouts/{session_id}
운동 기록 삭제. 본인 기록만 삭제 가능.

**Response**
```json
{ "deleted": true }
```

---

## AI 챗봇

### POST /chat
AI 챗봇 메시지 전송 및 응답.

**Request Body**
```json
{
  "message": "오늘 등 운동 50분 루틴 짜줘. 허리가 조금 불편해서 데드리프트는 빼줘."
}
```

**Response**
```json
{
  "message_id": "uuid",
  "response_text": "허리를 배려한 등 루틴을 준비했습니다...",
  "recommendation": {
    "id": "uuid",
    "workout_type": "weight",
    "structured_data": {
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
  }
}
```

> `recommendation`은 운동 추천 요청인 경우에만 포함됩니다. 일반 질문 응답 시 `null`.
> `recommendation.workout_type`은 `weight`, `running`, `other` 중 하나입니다.

---

## 통계

### GET /stats/weekly
주차별 총 운동 시간.

**Query Parameters**
| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| weeks | int | 4 | 조회할 주차 수 (4 또는 8) |

**Response**
```json
[
  { "week_start": "2026-06-22", "total_minutes": 180 },
  { "week_start": "2026-06-15", "total_minutes": 120 },
  { "week_start": "2026-06-08", "total_minutes": 0 },
  { "week_start": "2026-06-01", "total_minutes": 90 }
]
```

### GET /stats/summary
마이페이지 요약 카드 데이터.

**Response**
```json
{
  "this_week_minutes": 60,
  "total_sessions": 42,
  "last_workout_date": "2026-06-29"
}
```

---

## 에러 형식

```json
{
  "detail": "오류 메시지"
}
```

| HTTP 코드 | 상황 |
|---|---|
| 401 | 인증 토큰 없음 또는 유효하지 않음 |
| 403 | 타인의 리소스 접근 시도 |
| 404 | 리소스 없음 |
| 422 | 요청 데이터 유효성 오류 |
| 500 | 서버 내부 오류 |
