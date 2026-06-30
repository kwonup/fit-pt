'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { WORKOUT_TYPE_META } from '@/lib/constants'
import type { WorkoutDetail } from '@/types'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

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
        <p className="text-sm text-muted-foreground">불러오는 중...</p>
      </main>
    )
  }

  if (error || !workout) {
    return (
      <main className="mx-auto max-w-lg p-6">
        <p className="mb-4 text-sm text-destructive">{error ?? '기록이 없습니다.'}</p>
        <Link href="/calendar" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
          ← 캘린더로
        </Link>
      </main>
    )
  }

  const meta = WORKOUT_TYPE_META[workout.workout_type]

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-6 flex items-center justify-between">
        <Link href="/calendar" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
          ← 캘린더
        </Link>
        <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleting}>
          {deleting ? '삭제 중...' : '삭제'}
        </Button>
      </header>

      <div className="mb-2 flex items-center gap-2">
        <Badge variant="secondary" className={meta.badge}>
          {meta.label}
        </Badge>
        <span className="text-sm text-muted-foreground">{workout.workout_date}</span>
      </div>
      <h1 className="mb-6 text-2xl font-bold">{workout.title}</h1>

      {workout.workout_type === 'weight' && workout.exercises && (
        <section className="flex flex-col gap-3">
          {workout.exercises.map((ex) => (
            <Card key={ex.id} size="sm">
              <CardHeader>
                <CardTitle>{ex.exercise_name}</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                  {ex.weight_sets.map((s) => (
                    <li key={s.set_number} className="flex gap-3">
                      <span className="w-12">{s.set_number}세트</span>
                      <span className="text-foreground">
                        {s.weight_kg != null ? `${s.weight_kg}kg` : '-'} ×{' '}
                        {s.reps != null ? `${s.reps}회` : '-'}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </section>
      )}

      {workout.workout_type === 'running' && workout.running && (
        <Card>
          <CardContent>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-muted-foreground">거리</dt>
              <dd>{workout.running.distance_km ?? '-'} km</dd>
              <dt className="text-muted-foreground">소요 시간</dt>
              <dd>{workout.running.duration_minutes ?? '-'}분</dd>
              <dt className="text-muted-foreground">평균 페이스</dt>
              <dd>{workout.running.avg_pace ?? '-'}</dd>
              <dt className="text-muted-foreground">강도</dt>
              <dd>{workout.running.intensity ?? '-'}</dd>
            </dl>
          </CardContent>
        </Card>
      )}

      {workout.workout_type === 'other' && workout.other && (
        <Card>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm">{workout.other.content}</p>
          </CardContent>
        </Card>
      )}

      {(workout.duration_minutes != null || workout.memo) && (
        <section className="mt-4 flex flex-col gap-1 text-sm text-muted-foreground">
          {workout.workout_type !== 'running' && workout.duration_minutes != null && (
            <p>총 운동 시간: {workout.duration_minutes}분</p>
          )}
          {workout.memo && <p>메모: {workout.memo}</p>}
        </section>
      )}
    </main>
  )
}