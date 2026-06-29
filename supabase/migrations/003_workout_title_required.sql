-- 핏피티 (Fit PT) 스키마 변경 003
-- 운동 제목(title)을 DB 레벨에서 필수화
-- 1) 기존 NULL/빈 제목 백필: "날짜 + 타입" 형식
-- 2) NOT NULL + 빈 문자열 방지 CHECK 적용
-- Supabase SQL Editor 또는 supabase db push 로 실행

-- 1) 백필 (예: "2026-06-29 웨이트트레이닝")
UPDATE workout_sessions
SET title = workout_date::text || ' ' || CASE workout_type
  WHEN 'weight'  THEN '웨이트트레이닝'
  WHEN 'running' THEN '러닝'
  WHEN 'other'   THEN '기타'
  ELSE '운동'
END
WHERE title IS NULL OR btrim(title) = '';

-- 2) 필수 제약
ALTER TABLE workout_sessions ALTER COLUMN title SET NOT NULL;
ALTER TABLE workout_sessions
  ADD CONSTRAINT workout_sessions_title_not_blank
  CHECK (btrim(title) <> '');
