'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { X } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import type { WorkoutType } from '@/types'
import { Button, buttonVariants } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

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
        <h1 className="text-2xl font-bold">운동 기록</h1>
        <Link href="/dashboard" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
          취소
        </Link>
      </header>

      <Tabs value={type} onValueChange={(v) => setType(v as WorkoutType)} className="mb-6">
        <TabsList className="w-full">
          {(['weight', 'running', 'other'] as WorkoutType[]).map((t) => (
            <TabsTrigger key={t} value={t} className="flex-1">
              {TYPE_LABELS[t]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <section className="flex flex-col gap-1.5">
          <Label htmlFor="title">운동 제목</Label>
          <Input
            id="title"
            required
            maxLength={100}
            placeholder={TITLE_PLACEHOLDERS[type]}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </section>

        <section className="flex flex-col gap-1.5">
          <Label htmlFor="date">날짜</Label>
          <Input
            id="date"
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </section>

        {type === 'weight' && (
          <>
            <section className="flex flex-col gap-4">
              <Label>운동 종목</Label>
              {exercises.map((ex, ei) => (
                <Card key={ei} size="sm">
                  <CardContent className="flex flex-col gap-3">
                    <div className="flex items-center gap-2">
                      <Input
                        placeholder="종목명 (예: 벤치프레스)"
                        value={ex.exercise_name}
                        onChange={(e) => updateExercise(ei, { exercise_name: e.target.value })}
                      />
                      {exercises.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => setExercises((p) => p.filter((_, i) => i !== ei))}
                        >
                          삭제
                        </Button>
                      )}
                    </div>

                    <div className="flex flex-col gap-2">
                      {ex.sets.map((s, si) => (
                        <div key={si} className="flex items-center gap-2 text-sm">
                          <span className="w-12 text-muted-foreground">{si + 1}세트</span>
                          <Input
                            type="number"
                            min={0}
                            step="0.5"
                            placeholder="kg"
                            value={s.weight_kg}
                            onChange={(e) => updateSet(ei, si, { weight_kg: e.target.value })}
                            className="w-20"
                          />
                          <span className="text-muted-foreground">kg ×</span>
                          <Input
                            type="number"
                            min={0}
                            placeholder="회"
                            value={s.reps}
                            onChange={(e) => updateSet(ei, si, { reps: e.target.value })}
                            className="w-20"
                          />
                          <span className="text-muted-foreground">회</span>
                          {ex.sets.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-xs"
                              className="ml-auto"
                              onClick={() =>
                                updateExercise(ei, { sets: ex.sets.filter((_, i) => i !== si) })
                              }
                            >
                              <X />
                            </Button>
                          )}
                        </div>
                      ))}
                      <Button
                        type="button"
                        variant="link"
                        size="sm"
                        className="self-start px-0"
                        onClick={() => updateExercise(ei, { sets: [...ex.sets, newSet()] })}
                      >
                        + 세트 추가
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              <Button
                type="button"
                variant="outline"
                className="self-start border-dashed"
                onClick={() => setExercises((p) => [...p, newExercise()])}
              >
                + 종목 추가
              </Button>
            </section>

            <section className="flex flex-col gap-1.5">
              <Label htmlFor="w-duration">총 운동 시간 (분, 선택)</Label>
              <Input
                id="w-duration"
                type="number"
                min={1}
                placeholder="예: 60"
                value={weightDuration}
                onChange={(e) => setWeightDuration(e.target.value)}
              />
            </section>
          </>
        )}

        {type === 'running' && (
          <>
            <section className="flex flex-col gap-1.5">
              <Label htmlFor="distance">거리 (km)</Label>
              <Input
                id="distance"
                type="number"
                min={0}
                step="0.1"
                required
                placeholder="예: 5"
                value={distance}
                onChange={(e) => setDistance(e.target.value)}
              />
            </section>
            <section className="flex flex-col gap-1.5">
              <Label htmlFor="r-duration">소요 시간 (분)</Label>
              <Input
                id="r-duration"
                type="number"
                min={1}
                required
                placeholder="예: 40"
                value={runDuration}
                onChange={(e) => setRunDuration(e.target.value)}
              />
            </section>
            <section className="flex flex-col gap-1.5">
              <Label htmlFor="pace">평균 페이스 (선택, 비우면 자동 계산)</Label>
              <Input
                id="pace"
                placeholder="mm:ss (예: 8:00)"
                value={pace}
                onChange={(e) => setPace(e.target.value)}
              />
            </section>
            <section>
              <Label className="mb-2">강도 (선택)</Label>
              <div className="flex gap-2">
                {(['낮음', '보통', '높음'] as Intensity[]).map((lv) => (
                  <Button
                    type="button"
                    key={lv}
                    variant={intensity === lv ? 'default' : 'outline'}
                    onClick={() => setIntensity(intensity === lv ? '' : lv)}
                    className="flex-1"
                  >
                    {lv}
                  </Button>
                ))}
              </div>
            </section>
          </>
        )}

        {type === 'other' && (
          <>
            <section className="flex flex-col gap-1.5">
              <Label htmlFor="content">운동 내용</Label>
              <Textarea
                id="content"
                required
                rows={4}
                placeholder="예: 실내 클라이밍 1시간, 볼더링 V3 5개 완등"
                value={otherContent}
                onChange={(e) => setOtherContent(e.target.value)}
              />
            </section>
            <section className="flex flex-col gap-1.5">
              <Label htmlFor="o-duration">총 운동 시간 (분, 선택)</Label>
              <Input
                id="o-duration"
                type="number"
                min={1}
                placeholder="예: 60"
                value={otherDuration}
                onChange={(e) => setOtherDuration(e.target.value)}
              />
            </section>
          </>
        )}

        <section className="flex flex-col gap-1.5">
          <Label htmlFor="memo">메모 (선택)</Label>
          <Textarea
            id="memo"
            rows={2}
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
          />
        </section>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" size="lg" disabled={loading}>
          {loading ? '저장 중...' : '기록 저장'}
        </Button>
      </form>
    </main>
  )
}