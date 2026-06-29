-- 핏피티 (Fit PT) 스키마 변경 002
-- 1) 모든 운동 세션에 제목(title) 추가
-- 2) '기타(other)' 운동 타입 추가 + 자유 서술 저장용 other_sessions 테이블
-- 3) 웨이트 운동부위(muscle_group) 입력 제거 → NOT NULL 해제
-- Supabase SQL Editor 또는 supabase db push 로 실행

-- 1) 운동 제목 (웨이트/러닝/기타 공통)
ALTER TABLE workout_sessions ADD COLUMN IF NOT EXISTS title TEXT;

-- 2) workout_type에 'other' 허용
ALTER TABLE workout_sessions DROP CONSTRAINT IF EXISTS workout_sessions_workout_type_check;
ALTER TABLE workout_sessions
  ADD CONSTRAINT workout_sessions_workout_type_check
  CHECK (workout_type IN ('weight', 'running', 'other'));

-- 기타 세션 상세 (workout_sessions와 1:1, 자유 서술)
CREATE TABLE IF NOT EXISTS other_sessions (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL UNIQUE REFERENCES workout_sessions(id) ON DELETE CASCADE,
  content    TEXT NOT NULL
);

ALTER TABLE other_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "other_sessions: 본인 세션만" ON other_sessions
  FOR ALL USING (
    session_id IN (SELECT id FROM workout_sessions WHERE user_id = auth.uid())
  )
  WITH CHECK (
    session_id IN (SELECT id FROM workout_sessions WHERE user_id = auth.uid())
  );

-- 3) 웨이트 운동부위 입력 제거: 더 이상 필수가 아님
ALTER TABLE weight_exercises ALTER COLUMN muscle_group DROP NOT NULL;
