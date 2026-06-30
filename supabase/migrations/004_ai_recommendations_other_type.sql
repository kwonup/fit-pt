-- 핏피티 (Fit PT) 스키마 변경 004
-- AI 추천 이력에도 '기타(other)' 운동 타입 허용
-- Supabase SQL Editor 또는 supabase db push 로 실행

ALTER TABLE ai_recommendations DROP CONSTRAINT IF EXISTS ai_recommendations_workout_type_check;
ALTER TABLE ai_recommendations
  ADD CONSTRAINT ai_recommendations_workout_type_check
  CHECK (workout_type IN ('weight', 'running', 'other'));
