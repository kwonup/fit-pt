import type { Recommendation, WorkoutType } from '@/types'

// AI 추천을 "운동 기록하기" 화면으로 넘기기 위한 임시 저장소 키
const KEY = 'fitpt:workout-prefill'

export interface WorkoutPrefill {
  workout_type: WorkoutType
  structured_data: Recommendation
}

// 추천 카드 → /workouts/new 로 데이터 전달 (한 번 쓰고 버림)
export function setWorkoutPrefill(data: WorkoutPrefill) {
  if (typeof window === 'undefined') return
  sessionStorage.setItem(KEY, JSON.stringify(data))
}

// /workouts/new 진입 시 호출. 읽는 즉시 비워서 새로고침 때 중복 반영 방지.
export function takeWorkoutPrefill(): WorkoutPrefill | null {
  if (typeof window === 'undefined') return null
  const raw = sessionStorage.getItem(KEY)
  if (!raw) return null
  sessionStorage.removeItem(KEY)
  try {
    return JSON.parse(raw) as WorkoutPrefill
  } catch {
    return null
  }
}
