'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { createClient } from '@/lib/supabase/client'
import { PERSONAS } from '@/lib/constants'
import type { StatsSummary, UserProfile, WeeklyStat } from '@/types'

const fmtMonthDay = (iso: string) => {
  const [, m, d] = iso.split('-')
  return `${Number(m)}/${Number(d)}`
}

export default function DashboardPage() {
  const router = useRouter()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState<StatsSummary | null>(null)
  const [weekly, setWeekly] = useState<WeeklyStat[]>([])
  const [weeks, setWeeks] = useState<4 | 8>(4)

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
  const maxWeekMinutes = Math.max(1, ...weekly.map((w) => w.total_minutes))

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">핏피티</h1>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 underline-offset-2 hover:underline"
        >
          로그아웃
        </button>
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
          <button
            onClick={() => router.push('/onboarding')}
            className="mt-3 text-xs text-gray-500 underline-offset-2 hover:underline"
          >
            프로필 수정
          </button>
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
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-900">주간 운동 시간</h2>
            <div className="flex gap-1">
              {([4, 8] as const).map((w) => (
                <button
                  key={w}
                  onClick={() => setWeeks(w)}
                  className={`rounded-md px-2 py-1 text-xs transition ${
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

          {weekly.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">기록이 없습니다.</p>
          ) : (
            <div className="flex h-32 items-end gap-1.5">
              {weekly.map((w) => (
                <div key={w.week_start} className="flex flex-1 flex-col items-center gap-1">
                  <span className="text-[10px] text-gray-400">{w.total_minutes || ''}</span>
                  <div className="flex w-full flex-1 items-end">
                    <div
                      className="w-full rounded-t bg-gray-900"
                      style={{ height: `${(w.total_minutes / maxWeekMinutes) * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-400">{fmtMonthDay(w.week_start)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <nav className="grid gap-3">
        {[
          { label: 'AI 코치에게 루틴 받기', href: '/chat', soon: false },
          { label: '운동 기록하기', href: '/workouts/new', soon: false },
          { label: '캘린더', href: '/calendar', soon: false },
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
              className="flex items-center justify-between rounded-lg border border-gray-300 px-4 py-3 text-sm text-gray-900 transition hover:border-gray-900"
            >
              <span>{item.label}</span>
              <span className="text-gray-400">→</span>
            </Link>
          )
        )}
      </nav>
    </main>
  )
}
