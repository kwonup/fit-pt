'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { createClient } from '@/lib/supabase/client'
import { PERSONAS } from '@/lib/constants'
import type { UserProfile } from '@/types'

export default function DashboardPage() {
  const router = useRouter()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

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
      }
    }
    load()
  }, [router])

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

      <nav className="grid gap-3">
        {[
          { label: 'AI 코치에게 루틴 받기', href: '/chat', soon: true },
          { label: '운동 기록하기', href: '/workouts/new', soon: false },
          { label: '캘린더', href: '/calendar', soon: true },
          { label: '마이페이지', href: '/mypage', soon: true },
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
