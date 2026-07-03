-- 006_weekly_stats.sql
-- 대시보드 주간 막대그래프용 통계. 주(월요일 시작) 단위로 세 지표를 한 번에 집계한다.
--   total_minutes     : 운동 시간 합 (workout_sessions.duration_minutes)
--   total_volume      : 웨이트 볼륨 합 (weight_sets.weight_kg * reps)
--   total_distance_km : 러닝 거리 합 (running_sessions.distance_km)
-- 기록이 없는 주도 0으로 채워 p_weeks 개의 연속된 주를 반환한다.

create or replace function get_weekly_stats(p_user_id uuid, p_weeks int)
returns table (
  week_start        date,
  total_minutes     numeric,
  total_volume      numeric,
  total_distance_km numeric
)
language sql
stable
as $$
  with weeks as (
    select generate_series(
      (date_trunc('week', current_date)::date - ((p_weeks - 1) * 7)),
      date_trunc('week', current_date)::date,
      interval '7 days'
    )::date as week_start
  ),
  sess as (
    select
      date_trunc('week', ws.workout_date)::date as week_start,
      ws.id,
      coalesce(ws.duration_minutes, 0)          as duration_minutes
    from workout_sessions ws
    where ws.user_id = p_user_id
      and ws.workout_date >= (date_trunc('week', current_date)::date - ((p_weeks - 1) * 7))
  ),
  minutes as (
    select week_start, sum(duration_minutes) as total_minutes
    from sess
    group by week_start
  ),
  volume as (
    select s.week_start,
           sum(coalesce(wset.weight_kg, 0) * coalesce(wset.reps, 0)) as total_volume
    from sess s
    join weight_exercises we on we.session_id = s.id
    join weight_sets wset    on wset.exercise_id = we.id
    group by s.week_start
  ),
  distance as (
    select s.week_start,
           sum(coalesce(rs.distance_km, 0)) as total_distance_km
    from sess s
    join running_sessions rs on rs.session_id = s.id
    group by s.week_start
  )
  select
    w.week_start,
    coalesce(m.total_minutes, 0)     as total_minutes,
    coalesce(v.total_volume, 0)      as total_volume,
    coalesce(d.total_distance_km, 0) as total_distance_km
  from weeks w
  left join minutes  m on m.week_start = w.week_start
  left join volume   v on v.week_start = w.week_start
  left join distance d on d.week_start = w.week_start
  order by w.week_start;
$$;
