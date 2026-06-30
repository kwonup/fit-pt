'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { WORKOUT_TYPE_META } from '@/lib/constants'
import type { WorkoutDetail } from '@/types'

export default function WorkoutDetailPage() {
  const router = useRouter()
  const { id } = useParams<{ id: string }>()

  const [workout, setWorkout] = useState<WorkoutDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      const token = await getAccessToken()
      if (!token) {
        router.replace('/login')
        return
      }
      try {
        const data = await apiClient.get<WorkoutDetail>(`/workouts/${id}`, token)
        setWorkout(data)
      } catch {
        setError('기록을 불러오지 못했습니다.')
      }
      setLoading(false)
    }
    load()
  }, [id, router])

  async function handleDelete() {
    if (!confirm('이 운동 기록을 삭제할까요?')) return
    setDeleting(true)
    const token = await getAccessToken()
    if (!token) {
      router.replace('/login')
      return
    }
    try {
      await apiClient.delete(`/workouts/${id}`, token)
      router.push('/calendar')
      router.refresh()
    } catch {
      setError('삭제에 실패했습니다.')
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-gray-400">불러오는 중...</p>
      </main>
    )
  }

  if (error || !workout) {
    return (
      <main className="mx-auto max-w-lg p-6">
        <p className="mb-4 text-sm text-red-600">{error ?? '기록이 없습니다.'}</p>
        <Link href="/calendar" className="text-sm text-gray-500 hover:underline">
          ← 캘린더로
        </Link>
      </main>
    )
  }

  const meta = WORKOUT_TYPE_META[workout.workout_type]

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-6 flex items-center justify-between">
        <Link href="/calendar" className="text-sm text-gray-500 hover:underline">
          ← 캘린더
        </Link>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-sm text-gray-400 hover:text-red-600 disabled:opacity-50"
        >
          {deleting ? '삭제 중...' : '삭제'}
        </button>
      </header>

      <div className="mb-2 flex items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs ${meta.badge}`}>{meta.label}</span>
        <span className="text-sm text-gray-500">{workout.workout_date}</span>
      </div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">{workout.title}</h1>

      {workout.workout_type === 'weight' && workout.exercises && (
        <section className="flex flex-col gap-3">
          {workout.exercises.map((ex) => (
            <div key={ex.id} className="rounded-xl border border-gray-200 p-4">
              <h2 className="mb-2 text-sm font-medium text-gray-900">{ex.exercise_name}</h2>
              <ul className="flex flex-col gap-1 text-sm text-gray-600">
                {ex.weight_sets.map((s) => (
                  <li key={s.set_number} className="flex gap-3">
                    <span className="w-12 text-gray-400">{s.set_number}세트</span>
                    <span>
                      {s.weight_kg != null ? `${s.weight_kg}kg` : '-'} ×{' '}
                      {s.reps != null ? `${s.reps}회` : '-'}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      )}

      {workout.workout_type === 'running' && workout.running && (
        <section className="rounded-xl border border-gray-200 p-4">
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-gray-500">거리</dt>
            <dd className="text-gray-900">{workout.running.distance_km ?? '-'} km</dd>
            <dt className="text-gray-500">소요 시간</dt>
            <dd className="text-gray-900">{workout.running.duration_minutes ?? '-'}분</dd>
            <dt className="text-gray-500">평균 페이스</dt>
            <dd className="text-gray-900">{workout.running.avg_pace ?? '-'}</dd>
            <dt className="text-gray-500">강도</dt>
            <dd className="text-gray-900">{workout.running.intensity ?? '-'}</dd>
          </dl>
        </section>
      )}

      {workout.workout_type === 'other' && workout.other && (
        <section className="rounded-xl border border-gray-200 p-4">
          <p className="whitespace-pre-wrap text-sm text-gray-900">{workout.other.content}</p>
        </section>
      )}

      {(workout.duration_minutes != null || workout.memo) && (
        <section className="mt-4 flex flex-col gap-1 text-sm text-gray-500">
          {workout.workout_type !== 'running' && workout.duration_minutes != null && (
            <p>총 운동 시간: {workout.duration_minutes}분</p>
          )}
          {workout.memo && <p>메모: {workout.memo}</p>}
        </section>
      )}
    </main>
  )
}
