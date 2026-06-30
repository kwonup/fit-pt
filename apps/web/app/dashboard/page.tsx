'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import { ApiError, apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { createClient } from '@/lib/supabase/client'
import { PERSONAS } from '@/lib/constants'
import type { UserProfile } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

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
        <p className="text-sm text-muted-foreground">불러오는 중...</p>
      </main>
    )
  }

  const personaName = PERSONAS.find((p) => p.code === profile?.persona)?.name ?? '-'

  return (
    <main className="mx-auto max-w-lg p-6">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold">핏피티</h1>
        <Button variant="ghost" size="sm" onClick={handleLogout}>
          로그아웃
        </Button>
      </header>

      {profile && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>내 운동 프로필</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-muted-foreground">목표</dt>
              <dd>{profile.fitness_goals.join(', ') || '-'}</dd>
              <dt className="text-muted-foreground">숙련도</dt>
              <dd>{profile.fitness_level}</dd>
              <dt className="text-muted-foreground">주 운동 타입</dt>
              <dd>{profile.main_workout_type}</dd>
              <dt className="text-muted-foreground">주당 횟수</dt>
              <dd>{profile.weekly_frequency}회</dd>
              <dt className="text-muted-foreground">주의 부위</dt>
              <dd>{profile.caution_areas.join(', ') || '없음'}</dd>
              <dt className="text-muted-foreground">코치</dt>
              <dd>{personaName}</dd>
            </dl>
            <Button
              variant="link"
              size="sm"
              onClick={() => router.push('/onboarding')}
              className="mt-3 px-0 text-muted-foreground"
            >
              프로필 수정
            </Button>
          </CardContent>
        </Card>
      )}

      <nav className="grid gap-3">
        {[
          { label: 'AI 코치에게 루틴 받기', href: '/chat', soon: true },
          { label: '운동 기록하기', href: '/workouts/new', soon: false },
          { label: '캘린더', href: '/calendar', soon: false },
          { label: '마이페이지', href: '/mypage', soon: true },
        ].map((item) =>
          item.soon ? (
            <div
              key={item.href}
              className="flex items-center justify-between rounded-xl px-4 py-3 text-sm text-muted-foreground ring-1 ring-foreground/10"
            >
              <span>{item.label}</span>
              <span className="text-xs">준비 중</span>
            </div>
          ) : (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center justify-between rounded-xl px-4 py-3 text-sm ring-1 ring-foreground/10 transition hover:bg-muted"
            >
              <span>{item.label}</span>
              <ChevronRight className="size-4 text-muted-foreground" />
            </Link>
          )
        )}
      </nav>
    </main>
  )
}