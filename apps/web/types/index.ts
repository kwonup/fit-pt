// 트레이너 페르소나
export type Persona = 'angel' | 'tiger'

// 운동 타입
export type WorkoutType = 'weight' | 'running' | 'other'

// 숙련도
export type FitnessLevel = '초보' | '중급' | '고급'

// 운동 부위
export type MuscleGroup = '가슴' | '등' | '어깨' | '팔' | '하체' | '코어' | '전신'

// 사용자 프로필
export interface UserProfile {
  fitness_goals: string[]
  fitness_level: FitnessLevel
  main_workout_type: '웨이트트레이닝' | '러닝' | '둘다'
  weekly_frequency: number
  caution_areas: string[]
  persona: Persona
}

// 운동 세션 (기본)
export interface WorkoutSession {
  id: string
  workout_date: string
  workout_type: WorkoutType
  title: string | null
  duration_minutes: number | null
  memo: string | null
  ai_recommendation_id: string | null
  created_at: string
}

// 세트
export interface WorkoutSet {
  set_number: number
  weight_kg: number | null
  reps: number | null
}

// 저장된 웨이트 종목
export interface RecordedWeightExercise {
  id: string
  muscle_group: MuscleGroup | null
  exercise_name: string
  order_index: number
  sets: WorkoutSet[]
}

// 기타 세션 상세
export interface OtherSessionDetail extends WorkoutSession {
  content: string
}

// 웨이트 세션 상세
export interface WeightSessionDetail extends WorkoutSession {
  exercises: RecordedWeightExercise[]
}

// 러닝 세션 상세
export interface RunningSessionDetail extends WorkoutSession {
  distance_km: number
  avg_pace: string
  intensity: '낮음' | '보통' | '높음' | null
}

// 기록 상세 조회 응답 (GET /workouts/{id})
export interface DetailWeightExercise {
  id: string
  muscle_group: MuscleGroup | null
  exercise_name: string
  order_index: number
  weight_sets: WorkoutSet[]
}

export interface RunningDetail {
  distance_km: number | null
  duration_minutes: number | null
  avg_pace: string | null
  intensity: '낮음' | '보통' | '높음' | null
}

export interface OtherDetail {
  content: string
}

export interface WorkoutDetail extends WorkoutSession {
  exercises?: DetailWeightExercise[]
  running?: RunningDetail
  other?: OtherDetail
}

// AI 추천 세트
export interface RecommendedWeightSet extends WorkoutSet {
  rest_seconds?: number
}

// AI 추천 웨이트 종목
export interface RecommendedWeightExercise {
  name: string
  sets: RecommendedWeightSet[]
  notes?: string
}

// AI 추천 structured_data (웨이트)
export interface WeightRecommendation {
  type: 'weight'
  title: string
  estimated_duration_minutes: number
  muscle_group: MuscleGroup
  exercises: RecommendedWeightExercise[]
  cautions: string
}

// AI 추천 structured_data (러닝)
export interface RunningRecommendation {
  type: 'running'
  title: string
  total_duration_minutes: number
  distance_km: number
  avg_pace: string
  warmup: string
  main: string
  cooldown: string
  cautions: string
}

export type Recommendation = WeightRecommendation | RunningRecommendation

// 채팅 응답
export interface ChatResponse {
  message_id: string
  response_text: string
  recommendation: {
    id: string
    workout_type: WorkoutType
    structured_data: Recommendation
  } | null
}
