'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Check, Save } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import {
  CAUTION_AREAS,
  FITNESS_GOALS,
  FITNESS_LEVELS,
  MAIN_WORKOUT_TYPES,
  PERSONAS,
} from '@/lib/constants'
import { Button } from '@/components/ui/button'
import type { FitnessLevel, Persona, UserProfile } from '@/types'

export default function OnboardingPage() {
  const router = useRouter()

  const [goals, setGoals] = useState<string[]>([])
  const [level, setLevel] = useState<FitnessLevel>('초보')
  const [mainType, setMainType] = useState<UserProfile['main_workout_type']>('웨이트트레이닝')
  const [frequency, setFrequency] = useState(3)
  const [cautions, setCautions] = useState<string[]>([])
  const [persona, setPersona] = useState<Persona>('angel')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function toggle(list: string[], setList: (v: string[]) => void, value: string) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value])
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const token = await getAccessToken()
    if (!token) {
      router.replace('/login')
      return
    }

    try {
      await apiClient.put<UserProfile>(
        '/profile',
        {
          fitness_goals: goals,
          fitness_level: level,
          main_workout_type: mainType,
          weekly_frequency: frequency,
          caution_areas: cautions,
          persona,
        },
        token
      )
      router.replace('/dashboard')
      router.refresh()
    } catch {
      setError('프로필 저장에 실패했습니다. 잠시 후 다시 시도해주세요.')
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-lg p-6">
      <h1 className="mb-1 text-2xl font-bold text-gray-900">운동 프로필 설정</h1>
      <p className="mb-6 text-sm text-gray-500">
        AI 코치가 더 정확한 루틴을 추천하도록 기본 정보를 알려주세요.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <section>
          <label className="mb-2 block text-sm font-medium text-gray-900">운동 목표 (복수 선택)</label>
          <div className="flex flex-wrap gap-2">
            {FITNESS_GOALS.map((goal) => (
              <button
                type="button"
                key={goal}
                onClick={() => toggle(goals, setGoals, goal)}
                aria-pressed={goals.includes(goal)}
                className={`rounded-full border px-3 py-1.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 ${
                  goals.includes(goal)
                    ? 'border-gray-900 bg-gray-900 text-white'
                    : 'border-gray-300 text-gray-700 hover:border-gray-400'
                }`}
              >
                {goal}
              </button>
            ))}
          </div>
        </section>

        <section>
          <label className="mb-2 block text-sm font-medium text-gray-900">숙련도</label>
          <div className="flex gap-2">
            {FITNESS_LEVELS.map((lv) => (
              <button
                type="button"
                key={lv}
                onClick={() => setLevel(lv)}
                aria-pressed={level === lv}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 ${
                  level === lv
                    ? 'border-gray-900 bg-gray-900 text-white'
                    : 'border-gray-300 text-gray-700 hover:border-gray-400'
                }`}
              >
                {lv}
              </button>
            ))}
          </div>
        </section>

        <section>
          <label className="mb-2 block text-sm font-medium text-gray-900">주 운동 타입</label>
          <select
            value={mainType}
            onChange={(e) => setMainType(e.target.value as UserProfile['main_workout_type'])}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          >
            {MAIN_WORKOUT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </section>

        <section>
          <label className="mb-2 block text-sm font-medium text-gray-900">
            주당 운동 횟수: {frequency}회
          </label>
          <input
            type="range"
            min={1}
            max={7}
            value={frequency}
            onChange={(e) => setFrequency(Number(e.target.value))}
            className="w-full"
          />
        </section>

        <section>
          <label className="mb-2 block text-sm font-medium text-gray-900">
            주의 / 부상 부위 (선택)
          </label>
          <div className="flex flex-wrap gap-2">
            {CAUTION_AREAS.map((area) => (
              <button
                type="button"
                key={area}
                onClick={() => toggle(cautions, setCautions, area)}
                aria-pressed={cautions.includes(area)}
                className={`rounded-full border px-3 py-1.5 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 ${
                  cautions.includes(area)
                    ? 'border-red-500 bg-red-500 text-white'
                    : 'border-gray-300 text-gray-700 hover:border-gray-400'
                }`}
              >
                {area}
              </button>
            ))}
          </div>
        </section>

        <section>
          <label className="mb-2 block text-sm font-medium text-gray-900">트레이너 페르소나</label>
          <div className="flex flex-col gap-2">
            {PERSONAS.map((p) => (
              <button
                type="button"
                key={p.code}
                onClick={() => setPersona(p.code)}
                aria-pressed={persona === p.code}
                className={`rounded-xl border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 ${
                  persona === p.code
                    ? 'border-gray-900 bg-gray-50'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-gray-900">{p.name}</span>
                  {persona === p.code && (
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-900 text-white">
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500">{p.description}</div>
              </button>
            ))}
          </div>
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Button
          type="submit"
          disabled={loading || goals.length === 0}
          size="lg"
          className="w-full"
        >
          <Save data-icon="inline-start" aria-hidden="true" />
          {loading ? '저장 중...' : '시작하기'}
        </Button>
        {goals.length === 0 && (
          <p className="-mt-3 text-xs text-gray-400">운동 목표를 1개 이상 선택해주세요.</p>
        )}
      </form>
    </main>
  )
}
