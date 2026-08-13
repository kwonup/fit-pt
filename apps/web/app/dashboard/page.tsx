'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { CalendarDays, ChevronRight, Dumbbell, LogOut, Settings2, Sparkles } from 'lucide-react'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { createClient } from '@/lib/supabase/client'
import { PERSONAS } from '@/lib/constants'
import { Button } from '@/components/ui/button'
import type { StatsSummary, UserProfile, WeeklyStat } from '@/types'

const fmtMonthDay = (iso: string) => {
  const [, m, d] = iso.split('-')
  return `${Number(m)}/${Number(d)}`
}

type WeeklyMetric = 'time' | 'volume' | 'distance'

const round1 = (n: number) => Math.round(n * 10) / 10

const METRICS: Record<
  WeeklyMetric,
  { label: string; unit: string; value: (w: WeeklyStat) => number; format: (n: number) => string }
> = {
  time: {
    label: '시간',
    unit: '분',
    value: (w) => w.total_minutes,
    format: (n) => String(Math.round(n)),
  },
  volume: {
    label: '볼륨',
    unit: 'kg',
    value: (w) => w.total_volume,
    format: (n) => (n >= 1000 ? `${round1(n / 1000)}k` : String(Math.round(n))),
  },
  distance: {
    label: '러닝',
    unit: 'km',
    value: (w) => w.total_distance_km,
    format: (n) => String(round1(n)),
  },
}

export default function DashboardPage() {
  const router = useRouter()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<StatsSummary | null>(null)
  const [weekly, setWeekly] = useState<WeeklyStat[]>([])
  const [weeks, setWeeks] = useState<4 | 8>(4)
  const [metric, setMetric] = useState<WeeklyMetric>('time')
  const [loggingOut, setLoggingOut] = useState(false)

  useEffect(() => {
    async function load() {
      const token = await getAccessToken()
      if (!token) {
        router.replace('/login')
        return
      }
      try {
        const data = await apiClient.get<UserProfile>('/profile', token)
        setProfile(data)
        setLoading(false)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          router.replace('/onboarding')
          return
        }
        setLoading(false)
        return
      }
      try {
        const s = await apiClient.get<StatsSummary>('/stats/summary', token)
        setSummary(s)
      } catch {
        // 통계 실패는 무시 (대시보드 핵심 기능 아님)
      }
    }
    load()
  }, [router])

  useEffect(() => {
    async function loadWeekly() {
      const token = await getAccessToken()
      if (!token) return
      try {
        const data = await apiClient.get<WeeklyStat[]>(`/stats/weekly?weeks=${weeks}`, token)
        setWeekly(data)
      } catch {
        setWeekly([])
      }
    }
    loadWeekly()
  }, [weeks])

  async function handleLogout() {
    setLoggingOut(true)
    const supabase = createClient()
    await supabase.auth.signOut()
    router.replace('/login')
    router.refresh()
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-gray-400">불러오는 중...</p>
      </main>
    )
  }

  const personaName = PERSONAS.find((p) => p.code === profile?.persona)?.name ?? '-'
  const activeMetric = METRICS[metric]
  const maxWeekValue = Math.max(1, ...weekly.map((w) => activeMetric.value(w)))

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">핏피티</h1>
        <Button
          onClick={handleLogout}
          disabled={loggingOut}
          variant="outline"
          size="sm"
          className="text-gray-600"
        >
          <LogOut data-icon="inline-start" aria-hidden="true" />
          {loggingOut ? '로그아웃 중' : '로그아웃'}
        </Button>
      </header>

      {profile && (
        <section className="mb-8 rounded-xl border border-gray-200 p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-900">내 운동 프로필</h2>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-gray-500">목표</dt>
            <dd className="text-gray-900">{profile.fitness_goals.join(', ') || '-'}</dd>
            <dt className="text-gray-500">숙련도</dt>
            <dd className="text-gray-900">{profile.fitness_level}</dd>
            <dt className="text-gray-500">주 운동 타입</dt>
            <dd className="text-gray-900">{profile.main_workout_type}</dd>
            <dt className="text-gray-500">주당 횟수</dt>
            <dd className="text-gray-900">{profile.weekly_frequency}회</dd>
            <dt className="text-gray-500">주의 부위</dt>
            <dd className="text-gray-900">{profile.caution_areas.join(', ') || '없음'}</dd>
            <dt className="text-gray-500">코치</dt>
            <dd className="text-gray-900">{personaName}</dd>
          </dl>
          <Button
            onClick={() => router.push('/onboarding')}
            variant="outline"
            size="sm"
            className="mt-4"
          >
            <Settings2 data-icon="inline-start" aria-hidden="true" />
            프로필 수정
          </Button>
        </section>
      )}

      <section className="mb-8">
        <div className="mb-3 grid grid-cols-3 gap-2">
          <div className="rounded-xl border border-gray-200 p-3 text-center">
            <div className="text-xs text-gray-500">이번 주</div>
            <div className="mt-1 text-lg font-bold text-gray-900">
              {summary?.this_week_minutes ?? 0}
              <span className="text-xs font-normal text-gray-400">분</span>
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 p-3 text-center">
            <div className="text-xs text-gray-500">총 운동</div>
            <div className="mt-1 text-lg font-bold text-gray-900">
              {summary?.total_sessions ?? 0}
              <span className="text-xs font-normal text-gray-400">회</span>
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 p-3 text-center">
            <div className="text-xs text-gray-500">최근 운동</div>
            <div className="mt-1 text-lg font-bold text-gray-900">
              {summary?.last_workout_date ? fmtMonthDay(summary.last_workout_date) : '-'}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-900">
              주간 통계 <span className="text-xs font-normal text-gray-400">({activeMetric.unit})</span>
            </h2>
            <div className="flex gap-1">
              {([4, 8] as const).map((w) => (
                <button
                  key={w}
                  onClick={() => setWeeks(w)}
                  aria-pressed={weeks === w}
                  className={`rounded-md px-2 py-1 text-xs transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 ${
                    weeks === w
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  {w}주
                </button>
              ))}
            </div>
          </div>

          <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1">
            {(Object.keys(METRICS) as WeeklyMetric[]).map((key) => (
              <button
                key={key}
                onClick={() => setMetric(key)}
                aria-pressed={metric === key}
                className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 ${
                  metric === key
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {METRICS[key].label}
              </button>
            ))}
          </div>

          {weekly.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">기록이 없습니다.</p>
          ) : (
            <>
              <div className="flex items-end gap-1.5" style={{ height: 128 }}>
                {weekly.map((w) => {
                  const value = activeMetric.value(w)
                  const barPx = value > 0 ? Math.max(4, Math.round((value / maxWeekValue) * 104)) : 0
                  return (
                    <div
                      key={w.week_start}
                      className="flex flex-1 flex-col items-center justify-end gap-1"
                    >
                      <span className="text-[10px] leading-none text-gray-400">
                        {value ? activeMetric.format(value) : ''}
                      </span>
                      <div
                        className="w-full max-w-[12px] rounded-t bg-blue-400"
                        style={{ height: barPx }}
                      />
                    </div>
                  )
                })}
              </div>
              <div className="mt-1 flex gap-1.5">
                {weekly.map((w) => (
                  <span
                    key={w.week_start}
                    className="flex-1 text-center text-[10px] text-gray-400"
                  >
                    {fmtMonthDay(w.week_start)}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <nav className="grid gap-3">
        {[
          { label: 'AI 코치에게 루틴 받기', description: '내 기록에 맞는 운동 추천', href: '/chat', icon: Sparkles, soon: false },
          { label: '운동 기록하기', description: '오늘 운동을 직접 기록', href: '/workouts/new', icon: Dumbbell, soon: false },
          { label: '캘린더', description: '날짜별 운동 기록 확인', href: '/calendar', icon: CalendarDays, soon: false },
        ].map((item) =>
          item.soon ? (
            <div
              key={item.href}
              className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3 text-sm text-gray-400"
            >
              <span>{item.label}</span>
              <span className="text-xs">준비 중</span>
            </div>
          ) : (
            <Link
              key={item.href}
              href={item.href}
              className="group flex min-h-16 items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm transition-all hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gray-100 text-gray-700 transition group-hover:bg-gray-900 group-hover:text-white">
                <item.icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold text-gray-900">{item.label}</span>
                <span className="mt-0.5 block text-xs text-gray-500">{item.description}</span>
              </span>
              <ChevronRight className="h-4 w-4 text-gray-400 transition group-hover:translate-x-0.5 group-hover:text-gray-700" aria-hidden="true" />
            </Link>
          )
        )}
      </nav>
    </main>
  )
}
