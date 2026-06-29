'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { WORKOUT_TYPE_META } from '@/lib/constants'
import type { WorkoutSession } from '@/types'

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
        <Link href="/dashboard" className="text-sm text-gray-500 hover:underline">
          ← 대시보드
        </Link>
        <Link
          href="/workouts/new"
          className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700"
        >
          + 기록
        </Link>
      </header>

      <div className="mb-4 flex items-center justify-between">
        <button onClick={() => shiftMonth(-1)} className="px-2 py-1 text-gray-500 hover:text-gray-900">
          ‹
        </button>
        <h1 className="text-lg font-bold text-gray-900">
          {year}년 {month}월
        </h1>
        <button onClick={() => shiftMonth(1)} className="px-2 py-1 text-gray-500 hover:text-gray-900">
          ›
        </button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-xs text-gray-400">
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
              className={`flex aspect-square flex-col items-center justify-center rounded-lg border text-sm transition ${
                isSelected
                  ? 'border-gray-900 bg-gray-900 text-white'
                  : 'border-transparent text-gray-700 hover:border-gray-300'
              }`}
            >
              <span>{day}</span>
              <span className="mt-1 flex h-1.5 gap-0.5">
                {types.map((t) => (
                  <span key={t} className={`h-1.5 w-1.5 rounded-full ${WORKOUT_TYPE_META[t].dot}`} />
                ))}
              </span>
            </button>
          )
        })}
      </div>

      <div className="mt-6">
        {loading ? (
          <p className="text-center text-sm text-gray-400">불러오는 중...</p>
        ) : selected ? (
          selectedSessions.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {selectedSessions.map((s) => {
                const meta = WORKOUT_TYPE_META[s.workout_type]
                return (
                  <li key={s.id}>
                    <Link
                      href={`/workouts/${s.id}`}
                      className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3 transition hover:border-gray-900"
                    >
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs ${meta.badge}`}>
                          {meta.label}
                        </span>
                        <span className="text-sm text-gray-900">{s.title}</span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {s.duration_minutes ? `${s.duration_minutes}분` : ''} →
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="text-center text-sm text-gray-400">이 날의 기록이 없습니다.</p>
          )
        ) : (
          <p className="text-center text-sm text-gray-400">
            이번 달 {sessions.length}건의 기록 · 날짜를 선택하세요.
          </p>
        )}
      </div>
    </main>
  )
}
