import type { FitnessLevel, MuscleGroup, Persona } from '@/types'

export const FITNESS_GOALS = [
  '체중 감량',
  '근력 향상',
  '근육량 증가',
  '체력 향상',
  '운동 습관 형성',
  '바디 프로필',
] as const

export const FITNESS_LEVELS: FitnessLevel[] = ['초보', '중급', '고급']

export const MAIN_WORKOUT_TYPES = ['웨이트트레이닝', '러닝', '둘다'] as const

export const CAUTION_AREAS = ['목', '어깨', '허리', '무릎', '손목', '발목'] as const

export const MUSCLE_GROUPS: MuscleGroup[] = [
  '가슴',
  '등',
  '어깨',
  '팔',
  '하체',
  '코어',
  '전신',
]

export const PERSONAS: { code: Persona; name: string; description: string }[] = [
  {
    code: 'angel',
    name: '상냥한 천사 코치',
    description: '따뜻하게 격려하며 부드럽게 이끌어주는 말투',
  },
  {
    code: 'tiger',
    name: '엄격한 호랑이 코치',
    description: '직설적이고 단호하게 동기를 끌어올리는 말투',
  },
]
