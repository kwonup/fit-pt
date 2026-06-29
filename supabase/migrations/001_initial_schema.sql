-- 핏피티 (Fit PT) 초기 스키마
-- Supabase 대시보드 SQL Editor 또는 supabase db push 로 실행

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================
-- user_profiles
-- auth.users와 1:1 관계
-- =========================================
CREATE TABLE user_profiles (
  id                 UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  fitness_goals      TEXT[]      DEFAULT '{}',
  fitness_level      TEXT        CHECK (fitness_level IN ('초보', '중급', '고급')),
  main_workout_type  TEXT        CHECK (main_workout_type IN ('웨이트트레이닝', '러닝', '둘다')),
  weekly_frequency   INT         CHECK (weekly_frequency BETWEEN 1 AND 7),
  caution_areas      TEXT[]      DEFAULT '{}',
  persona            TEXT        CHECK (persona IN ('angel', 'tiger')) DEFAULT 'angel',
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================
-- workout_sessions
-- 하나의 운동 세션 (웨이트 or 러닝)
-- =========================================
CREATE TABLE workout_sessions (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id               UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  workout_date          DATE        NOT NULL,
  workout_type          TEXT        NOT NULL CHECK (workout_type IN ('weight', 'running')),
  duration_minutes      INT,
  memo                  TEXT,
  ai_recommendation_id  UUID,       -- 운동반영하기로 생성된 경우 (FK는 아래에 추가)
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================
-- weight_exercises
-- 웨이트 세션의 운동 종목
-- =========================================
CREATE TABLE weight_exercises (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id    UUID NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
  muscle_group  TEXT NOT NULL,
  exercise_name TEXT NOT NULL,
  order_index   INT  NOT NULL DEFAULT 0
);

-- =========================================
-- weight_sets
-- 운동 종목의 세트별 데이터
-- =========================================
CREATE TABLE weight_sets (
  id          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
  exercise_id UUID    NOT NULL REFERENCES weight_exercises(id) ON DELETE CASCADE,
  set_number  INT     NOT NULL,
  weight_kg   NUMERIC(5, 2),
  reps        INT
);

-- =========================================
-- running_sessions
-- 러닝 세션 상세 (workout_sessions와 1:1)
-- =========================================
CREATE TABLE running_sessions (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id       UUID    NOT NULL UNIQUE REFERENCES workout_sessions(id) ON DELETE CASCADE,
  distance_km      NUMERIC(5, 2),
  duration_minutes INT,
  avg_pace         TEXT,  -- 형식: "mm:ss" (예: "8:30")
  intensity        TEXT    CHECK (intensity IN ('낮음', '보통', '높음'))
);

-- =========================================
-- ai_recommendations
-- AI 추천 이력 및 구조화 데이터 (운동반영하기의 입력값)
-- =========================================
CREATE TABLE ai_recommendations (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  user_message      TEXT NOT NULL,
  ai_response_text  TEXT NOT NULL,
  structured_data   JSONB,  -- 운동반영하기 기능의 핵심: 파싱 가능한 구조화된 루틴
  workout_type      TEXT    CHECK (workout_type IN ('weight', 'running')),
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- workout_sessions.ai_recommendation_id FK (순환 참조 해결을 위해 분리)
ALTER TABLE workout_sessions
  ADD CONSTRAINT fk_ai_recommendation
  FOREIGN KEY (ai_recommendation_id) REFERENCES ai_recommendations(id);

-- =========================================
-- chat_messages
-- 채팅 메시지 이력
-- =========================================
CREATE TABLE chat_messages (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role              TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content           TEXT NOT NULL,
  recommendation_id UUID REFERENCES ai_recommendations(id),
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================
-- 조회 성능 인덱스
-- 캘린더, 통계, 채팅 이력 조회에 사용
-- =========================================
CREATE INDEX idx_workout_sessions_user_date ON workout_sessions(user_id, workout_date DESC);
CREATE INDEX idx_ai_recommendations_user_created_at ON ai_recommendations(user_id, created_at DESC);
CREATE INDEX idx_chat_messages_user_created_at ON chat_messages(user_id, created_at ASC);
CREATE INDEX idx_weight_exercises_session_order ON weight_exercises(session_id, order_index ASC);
CREATE INDEX idx_weight_sets_exercise_set_number ON weight_sets(exercise_id, set_number ASC);

-- =========================================
-- Row Level Security (RLS)
-- 모든 테이블: 본인 데이터만 접근 가능
-- =========================================
ALTER TABLE user_profiles      ENABLE ROW LEVEL SECURITY;
ALTER TABLE workout_sessions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE weight_exercises   ENABLE ROW LEVEL SECURITY;
ALTER TABLE weight_sets        ENABLE ROW LEVEL SECURITY;
ALTER TABLE running_sessions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages      ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_profiles: 본인만" ON user_profiles
  FOR ALL USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

CREATE POLICY "workout_sessions: 본인만" ON workout_sessions
  FOR ALL USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "weight_exercises: 본인 세션만" ON weight_exercises
  FOR ALL USING (
    session_id IN (SELECT id FROM workout_sessions WHERE user_id = auth.uid())
  )
  WITH CHECK (
    session_id IN (SELECT id FROM workout_sessions WHERE user_id = auth.uid())
  );

CREATE POLICY "weight_sets: 본인 운동만" ON weight_sets
  FOR ALL USING (
    exercise_id IN (
      SELECT we.id FROM weight_exercises we
      JOIN workout_sessions ws ON we.session_id = ws.id
      WHERE ws.user_id = auth.uid()
    )
  )
  WITH CHECK (
    exercise_id IN (
      SELECT we.id FROM weight_exercises we
      JOIN workout_sessions ws ON we.session_id = ws.id
      WHERE ws.user_id = auth.uid()
    )
  );

CREATE POLICY "running_sessions: 본인 세션만" ON running_sessions
  FOR ALL USING (
    session_id IN (SELECT id FROM workout_sessions WHERE user_id = auth.uid())
  )
  WITH CHECK (
    session_id IN (SELECT id FROM workout_sessions WHERE user_id = auth.uid())
  );

CREATE POLICY "ai_recommendations: 본인만" ON ai_recommendations
  FOR ALL USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "chat_messages: 본인만" ON chat_messages
  FOR ALL USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- =========================================
-- updated_at 자동 갱신 트리거
-- =========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_workout_sessions_updated_at
  BEFORE UPDATE ON workout_sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
