'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { cn } from '@/lib/utils'
import {
  CAUTION_AREAS,
  FITNESS_GOALS,
  FITNESS_LEVELS,
  MAIN_WORKOUT_TYPES,
  PERSONAS,
} from '@/lib/constants'
import type { FitnessLevel, Persona, UserProfile } from '@/types'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'

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
      <h1 className="mb-1 text-2xl font-bold">운동 프로필 설정</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        AI 코치가 더 정확한 루틴을 추천하도록 기본 정보를 알려주세요.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <section>
          <Label className="mb-2">운동 목표 (복수 선택)</Label>
          <div className="flex flex-wrap gap-2">
            {FITNESS_GOALS.map((goal) => (
              <Button
                type="button"
                key={goal}
                size="sm"
                variant={goals.includes(goal) ? 'default' : 'outline'}
                onClick={() => toggle(goals, setGoals, goal)}
              >
                {goal}
              </Button>
            ))}
          </div>
        </section>

        <section>
          <Label className="mb-2">숙련도</Label>
          <div className="flex gap-2">
            {FITNESS_LEVELS.map((lv) => (
              <Button
                type="button"
                key={lv}
                variant={level === lv ? 'default' : 'outline'}
                onClick={() => setLevel(lv)}
                className="flex-1"
              >
                {lv}
              </Button>
            ))}
          </div>
        </section>

        <section>
          <Label className="mb-2">주 운동 타입</Label>
          <div className="flex gap-2">
            {MAIN_WORKOUT_TYPES.map((t) => (
              <Button
                type="button"
                key={t}
                variant={mainType === t ? 'default' : 'outline'}
                onClick={() => setMainType(t)}
                className="flex-1"
              >
                {t}
              </Button>
            ))}
          </div>
        </section>

        <section>
          <Label className="mb-2">주당 운동 횟수: {frequency}회</Label>
          <input
            type="range"
            min={1}
            max={7}
            value={frequency}
            onChange={(e) => setFrequency(Number(e.target.value))}
            className="w-full accent-primary"
          />
        </section>

        <section>
          <Label className="mb-2">주의 / 부상 부위 (선택)</Label>
          <div className="flex flex-wrap gap-2">
            {CAUTION_AREAS.map((area) => {
              const active = cautions.includes(area)
              return (
                <Button
                  type="button"
                  key={area}
                  size="sm"
                  variant={active ? 'default' : 'outline'}
                  onClick={() => toggle(cautions, setCautions, area)}
                  className={cn(active && 'bg-destructive text-white hover:bg-destructive/90')}
                >
                  {area}
                </Button>
              )
            })}
          </div>
        </section>

        <section>
          <Label className="mb-2">트레이너 페르소나</Label>
          <div className="flex flex-col gap-2">
            {PERSONAS.map((p) => (
              <button
                type="button"
                key={p.code}
                onClick={() => setPersona(p.code)}
                className={cn(
                  'rounded-xl px-4 py-3 text-left transition',
                  persona === p.code
                    ? 'bg-muted ring-2 ring-primary'
                    : 'ring-1 ring-foreground/10 hover:bg-muted'
                )}
              >
                <div className="text-sm font-medium">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.description}</div>
              </button>
            ))}
          </div>
        </section>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" size="lg" disabled={loading || goals.length === 0}>
          {loading ? '저장 중...' : '시작하기'}
        </Button>
        {goals.length === 0 && (
          <p className="-mt-3 text-xs text-muted-foreground">운동 목표를 1개 이상 선택해주세요.</p>
        )}
      </form>
    </main>
  )
}