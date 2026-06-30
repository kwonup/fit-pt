-- 005_weight_exercise_maxes.sql
-- AI 추천에 "종목별 역대 최고 중량 + 최근 작업 중량"을 활용하기 위한 집계 함수.
-- 전체 기간을 대상으로 하되, 개별 세트가 아니라 종목 단위로 집계해서 반환한다(토큰/네트워크 절약).
-- 백엔드는 service_role 로 호출하므로 RLS 우회 + 함수 내 p_user_id 필터로 본인 데이터만 집계한다.

create or replace function get_weight_exercise_maxes(p_user_id uuid)
returns table (
  exercise_name     text,
  session_count     bigint,
  best_weight_kg    numeric,
  best_reps         int,
  last_workout_date date,
  recent_weight_kg  numeric,
  recent_reps       int
)
language sql
stable
as $$
  with sets as (
    select
      lower(btrim(we.exercise_name)) as norm_name,
      we.exercise_name               as raw_name,
      ws.workout_date,
      s.weight_kg,
      s.reps
    from weight_sets s
    join weight_exercises we on we.id = s.exercise_id
    join workout_sessions ws on ws.id = we.session_id
    where ws.user_id = p_user_id
      and s.weight_kg is not null
  ),
  -- 역대 최고 중량 세트 (동률이면 reps 많은 쪽)
  best as (
    select distinct on (norm_name)
      norm_name,
      weight_kg as best_weight_kg,
      reps      as best_reps
    from sets
    order by norm_name, weight_kg desc, reps desc nulls last
  ),
  -- 가장 최근 운동일의 최고 중량 세트 (최근 작업 중량)
  recent as (
    select distinct on (norm_name)
      norm_name,
      workout_date as last_workout_date,
      weight_kg    as recent_weight_kg,
      reps         as recent_reps
    from sets
    order by norm_name, workout_date desc, weight_kg desc nulls last
  ),
  agg as (
    select
      norm_name,
      max(raw_name)              as display_name,
      count(distinct workout_date) as session_count
    from sets
    group by norm_name
  )
  select
    a.display_name as exercise_name,
    a.session_count,
    b.best_weight_kg,
    b.best_reps,
    r.last_workout_date,
    r.recent_weight_kg,
    r.recent_reps
  from agg a
  join best b   on b.norm_name = a.norm_name
  join recent r on r.norm_name = a.norm_name
  order by a.session_count desc, b.best_weight_kg desc
  limit 15;
$$;
