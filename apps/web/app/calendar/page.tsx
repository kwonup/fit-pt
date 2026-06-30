'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { WORKOUT_TYPE_META } from '@/lib/constants'
import { cn } from '@/lib/utils'
import type { WorkoutSession } from '@/types'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

const pad = (n: number) => String(n).padStart(2, '0')
const dateKey = (y: number, m: number, d: number) => `${y}-${pad(m)}-${pad(d)}`

export default function CalendarPage() {
  const router = useRouter()
  const now = new Date()

  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [sessions, setSessions] = useState<WorkoutSession[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    const token = await getAccessToken()
    if (!token) {
      router.replace('/login')
      return
    }
    try {
      const data = await apiClient.get<WorkoutSession[]>(
        `/workouts?year=${year}&month=${month}`,
        token
      )
      setSessions(data)
    } catch {
      setSessions([])
    }
    setLoading(false)
  }, [router, year, month])

  useEffect(() => {
    load()
  }, [load])

  function shiftMonth(delta: number) {
    setSelected(null)
    const next = month + delta
    if (next < 1) {
      setYear(year - 1)
      setMonth(12)
    } else if (next > 12) {
      setYear(year + 1)
      setMonth(1)
    } else {
      setMonth(next)
    }
  }

  const byDate = new Map<string, WorkoutSession[]>()
  for (const s of sessions) {
    const list = byDate.get(s.workout_date) ?? []
    list.push(s)
    byDate.set(s.workout_date, list)
  }

  const firstWeekday = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]

  const selectedSessions = selected ? byDate.get(selected) ?? [] : []

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-6 flex items-center justify-between">
        <Link href="/dashboard" className={buttonVariants({ variant: 'ghost', size: 'sm' })}>
          ← 대시보드
        </Link>
        <Link href="/workouts/new" className={buttonVariants({ size: 'sm' })}>
          + 기록
        </Link>
      </header>

      <div className="mb-4 flex items-center justify-between">
        <Button variant="ghost" size="icon-sm" onClick={() => shiftMonth(-1)}>
          <ChevronLeft />
        </Button>
        <h1 className="text-lg font-bold">
          {year}년 {month}월
        </h1>
        <Button variant="ghost" size="icon-sm" onClick={() => shiftMonth(1)}>
          <ChevronRight />
        </Button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
        {WEEKDAYS.map((w) => (
          <div key={w} className="py-1">
            {w}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, i) => {
          if (day === null) return <div key={`blank-${i}`} />
          const key = dateKey(year, month, day)
          const daySessions = byDate.get(key) ?? []
          const types = Array.from(new Set(daySessions.map((s) => s.workout_type)))
          const isSelected = selected === key
          return (
            <button
              key={key}
              onClick={() => setSelected(isSelected ? null : key)}
              className={cn(
                'flex aspect-square flex-col items-center justify-center rounded-lg text-sm transition',
                isSelected ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
              )}
            >
              <span>{day}</span>
              <span className="mt-1 flex h-1.5 gap-0.5">
                {types.map((t) => (
                  <span key={t} className={cn('h-1.5 w-1.5 rounded-full', WORKOUT_TYPE_META[t].dot)} />
                ))}
              </span>
            </button>
          )
        })}
      </div>

      <div className="mt-6">
        {loading ? (
          <p className="text-center text-sm text-muted-foreground">불러오는 중...</p>
        ) : selected ? (
          selectedSessions.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {selectedSessions.map((s) => {
                const meta = WORKOUT_TYPE_META[s.workout_type]
                return (
                  <li key={s.id}>
                    <Link
                      href={`/workouts/${s.id}`}
                      className="flex items-center justify-between rounded-xl px-4 py-3 ring-1 ring-foreground/10 transition hover:bg-muted"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className={meta.badge}>
                          {meta.label}
                        </Badge>
                        <span className="text-sm">{s.title}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {s.duration_minutes ? `${s.duration_minutes}분` : ''}
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="text-center text-sm text-muted-foreground">이 날의 기록이 없습니다.</p>
          )
        ) : (
          <p className="text-center text-sm text-muted-foreground">
            이번 달 {sessions.length}건의 기록 · 날짜를 선택하세요.
          </p>
        )}
      </div>
    </main>
  )
}