'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { takeWorkoutPrefill } from '@/lib/workout-prefill'
import type { WorkoutType } from '@/types'

type SetInput = { weight_kg: string; reps: string }
type ExerciseInput = { exercise_name: string; sets: SetInput[] }
type Intensity = '낮음' | '보통' | '높음'

const today = () => new Date().toISOString().slice(0, 10)
const newSet = (): SetInput => ({ weight_kg: '', reps: '' })
const newExercise = (): ExerciseInput => ({ exercise_name: '', sets: [newSet()] })

const TYPE_LABELS: Record<WorkoutType, string> = {
  weight: '웨이트트레이닝',
  running: '러닝',
  other: '기타',
}

const TITLE_PLACEHOLDERS: Record<WorkoutType, string> = {
  weight: '예: 저녁 등 워크아웃',
  running: '예: 아침 인터벌 러닝',
  other: '예: 주말 클라이밍',
}

export default function NewWorkoutPage() {
  const router = useRouter()

  const [type, setType] = useState<WorkoutType>('weight')
  const [title, setTitle] = useState('')
  const [date, setDate] = useState(today)
  const [memo, setMemo] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 웨이트
  const [weightDuration, setWeightDuration] = useState('')
  const [exercises, setExercises] = useState<ExerciseInput[]>([newExercise()])

  // 러닝
  const [distance, setDistance] = useState('')
  const [runDuration, setRunDuration] = useState('')
  const [pace, setPace] = useState('')
  const [intensity, setIntensity] = useState<Intensity | ''>('')

  // 기타
  const [otherContent, setOtherContent] = useState('')
  const [otherDuration, setOtherDuration] = useState('')

  // AI 추천 카드에서 넘어온 경우 폼을 미리 채운다.
  useEffect(() => {
    const prefill = takeWorkoutPrefill()
    if (!prefill) return
    const { workout_type, structured_data: rec } = prefill

    setType(workout_type)
    setTitle(rec.title)

    if (rec.type === 'weight') {
      setExercises(
        rec.exercises.map((ex) => ({
          exercise_name: ex.name,
          sets: ex.sets.map((s) => ({
            weight_kg: s.weight_kg != null ? String(s.weight_kg) : '',
            reps: s.reps != null ? String(s.reps) : '',
          })),
        }))
      )
      if (rec.estimated_duration_minutes) setWeightDuration(String(rec.estimated_duration_minutes))
      if (rec.cautions) setMemo(`⚠️ ${rec.cautions}`)
    } else if (rec.type === 'running') {
      setDistance(String(rec.distance_km))
      setRunDuration(String(rec.total_duration_minutes))
      if (rec.avg_pace) setPace(rec.avg_pace)
      const lines = [
        rec.warmup && `웜업: ${rec.warmup}`,
        rec.main && `본운동: ${rec.main}`,
        rec.cooldown && `쿨다운: ${rec.cooldown}`,
        rec.cautions && `⚠️ ${rec.cautions}`,
      ].filter(Boolean)
      if (lines.length) setMemo(lines.join('\n'))
    } else {
      setOtherContent(rec.content)
      if (rec.estimated_duration_minutes) setOtherDuration(String(rec.estimated_duration_minutes))
      if (rec.cautions) setMemo(`⚠️ ${rec.cautions}`)
    }
  }, [])

  function updateExercise(i: number, patch: Partial<ExerciseInput>) {
    setExercises((prev) => prev.map((ex, idx) => (idx === i ? { ...ex, ...patch } : ex)))
  }

  function updateSet(ei: number, si: number, patch: Partial<SetInput>) {
    setExercises((prev) =>
      prev.map((ex, idx) =>
        idx === ei
          ? { ...ex, sets: ex.sets.map((s, sIdx) => (sIdx === si ? { ...s, ...patch } : s)) }
          : ex
      )
    )
  }

  async function submitWeight(token: string) {
    const cleaned = exercises
      .filter((ex) => ex.exercise_name.trim())
      .map((ex, index) => ({
        exercise_name: ex.exercise_name.trim(),
        order_index: index,
        sets: ex.sets.map((s, sIdx) => ({
          set_number: sIdx + 1,
          weight_kg: s.weight_kg === '' ? null : Number(s.weight_kg),
          reps: s.reps === '' ? null : Number(s.reps),
        })),
      }))

    if (cleaned.length === 0) {
      throw new Error('운동 종목을 1개 이상 입력해주세요.')
    }

    await apiClient.post(
      '/workouts/weight',
      {
        workout_date: date,
        title: title.trim(),
        duration_minutes: weightDuration === '' ? null : Number(weightDuration),
        memo: memo || null,
        exercises: cleaned,
      },
      token
    )
  }

  async function submitRunning(token: string) {
    if (distance === '' || Number(distance) <= 0) {
      throw new Error('거리를 입력해주세요.')
    }
    if (runDuration === '' || Number(runDuration) < 1) {
      throw new Error('소요 시간을 입력해주세요.')
    }

    await apiClient.post(
      '/workouts/running',
      {
        workout_date: date,
        title: title.trim(),
        distance_km: Number(distance),
        duration_minutes: Number(runDuration),
        avg_pace: pace || undefined,
        intensity: intensity || undefined,
        memo: memo || null,
      },
      token
    )
  }

  async function submitOther(token: string) {
    if (!otherContent.trim()) {
      throw new Error('운동 내용을 입력해주세요.')
    }

    await apiClient.post(
      '/workouts/other',
      {
        workout_date: date,
        title: title.trim(),
        content: otherContent.trim(),
        duration_minutes: otherDuration === '' ? null : Number(otherDuration),
        memo: memo || null,
      },
      token
    )
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (!title.trim()) {
      setError('운동 제목을 입력해주세요.')
      setLoading(false)
      return
    }

    const token = await getAccessToken()
    if (!token) {
      router.replace('/login')
      return
    }

    try {
      if (type === 'weight') await submitWeight(token)
      else if (type === 'running') await submitRunning(token)
      else await submitOther(token)
      router.push('/dashboard')
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : '저장에 실패했습니다.')
      setLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">운동 기록</h1>
        <Link href="/dashboard" className="text-sm text-gray-500 hover:underline">
          취소
        </Link>
      </header>

      <div className="mb-6 flex gap-2">
        {(['weight', 'running', 'other'] as WorkoutType[]).map((t) => (
          <button
            type="button"
            key={t}
            onClick={() => setType(t)}
            className={`flex-1 rounded-lg border px-3 py-2 text-sm transition ${
              type === t
                ? 'border-gray-900 bg-gray-900 text-white'
                : 'border-gray-300 text-gray-700 hover:border-gray-400'
            }`}
          >
            {TYPE_LABELS[t]}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <section>
          <label className="mb-1 block text-sm font-medium text-gray-900">운동 제목</label>
          <input
            type="text"
            required
            maxLength={100}
            placeholder={TITLE_PLACEHOLDERS[type]}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          />
        </section>

        <section>
          <label className="mb-1 block text-sm font-medium text-gray-900">날짜</label>
          <input
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          />
        </section>

        {type === 'weight' && (
          <>
            <section className="flex flex-col gap-4">
              <label className="block text-sm font-medium text-gray-900">운동 종목</label>
              {exercises.map((ex, ei) => (
                <div key={ei} className="rounded-xl border border-gray-200 p-3">
                  <div className="mb-3 flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="종목명 (예: 벤치프레스)"
                      value={ex.exercise_name}
                      onChange={(e) => updateExercise(ei, { exercise_name: e.target.value })}
                      className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                    {exercises.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setExercises((p) => p.filter((_, i) => i !== ei))}
                        className="text-sm text-gray-400 hover:text-red-600"
                      >
                        삭제
                      </button>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    {ex.sets.map((s, si) => (
                      <div key={si} className="flex items-center gap-2 text-sm">
                        <span className="w-12 text-gray-500">{si + 1}세트</span>
                        <input
                          type="number"
                          min={0}
                          step="0.5"
                          placeholder="kg"
                          value={s.weight_kg}
                          onChange={(e) => updateSet(ei, si, { weight_kg: e.target.value })}
                          className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 focus:border-gray-900 focus:outline-none"
                        />
                        <span className="text-gray-400">kg ×</span>
                        <input
                          type="number"
                          min={0}
                          placeholder="회"
                          value={s.reps}
                          onChange={(e) => updateSet(ei, si, { reps: e.target.value })}
                          className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 focus:border-gray-900 focus:outline-none"
                        />
                        <span className="text-gray-400">회</span>
                        {ex.sets.length > 1 && (
                          <button
                            type="button"
                            onClick={() =>
                              updateExercise(ei, { sets: ex.sets.filter((_, i) => i !== si) })
                            }
                            className="ml-auto text-gray-400 hover:text-red-600"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() => updateExercise(ei, { sets: [...ex.sets, newSet()] })}
                      className="self-start text-xs text-gray-500 hover:underline"
                    >
                      + 세트 추가
                    </button>
                  </div>
                </div>
              ))}
              <button
                type="button"
                onClick={() => setExercises((p) => [...p, newExercise()])}
                className="self-start rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-400"
              >
                + 종목 추가
              </button>
            </section>

            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">
                총 운동 시간 (분, 선택)
              </label>
              <input
                type="number"
                min={1}
                placeholder="예: 60"
                value={weightDuration}
                onChange={(e) => setWeightDuration(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </section>
          </>
        )}

        {type === 'running' && (
          <>
            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">거리 (km)</label>
              <input
                type="number"
                min={0}
                step="0.1"
                required
                placeholder="예: 5"
                value={distance}
                onChange={(e) => setDistance(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </section>
            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">소요 시간 (분)</label>
              <input
                type="number"
                min={1}
                required
                placeholder="예: 40"
                value={runDuration}
                onChange={(e) => setRunDuration(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </section>
            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">
                평균 페이스 (선택, 비우면 자동 계산)
              </label>
              <input
                type="text"
                placeholder="mm:ss (예: 8:00)"
                value={pace}
                onChange={(e) => setPace(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </section>
            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">강도 (선택)</label>
              <div className="flex gap-2">
                {(['낮음', '보통', '높음'] as Intensity[]).map((lv) => (
                  <button
                    type="button"
                    key={lv}
                    onClick={() => setIntensity(intensity === lv ? '' : lv)}
                    className={`flex-1 rounded-lg border px-3 py-2 text-sm transition ${
                      intensity === lv
                        ? 'border-gray-900 bg-gray-900 text-white'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {lv}
                  </button>
                ))}
              </div>
            </section>
          </>
        )}

        {type === 'other' && (
          <>
            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">운동 내용</label>
              <textarea
                rows={4}
                required
                placeholder="예: 실내 클라이밍 1시간, 볼더링 V3 5개 완등"
                value={otherContent}
                onChange={(e) => setOtherContent(e.target.value)}
                className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </section>
            <section>
              <label className="mb-1 block text-sm font-medium text-gray-900">
                총 운동 시간 (분, 선택)
              </label>
              <input
                type="number"
                min={1}
                placeholder="예: 60"
                value={otherDuration}
                onChange={(e) => setOtherDuration(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </section>
          </>
        )}

        <section>
          <label className="mb-1 block text-sm font-medium text-gray-900">메모 (선택)</label>
          <textarea
            rows={2}
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          />
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-gray-900 px-4 py-3 text-sm font-medium text-white transition hover:bg-gray-700 disabled:opacity-50"
        >
          {loading ? '저장 중...' : '기록 저장'}
        </button>
      </form>
    </main>
  )
}
