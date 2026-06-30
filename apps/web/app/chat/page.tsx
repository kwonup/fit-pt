'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { setWorkoutPrefill } from '@/lib/workout-prefill'
import { RecommendationCard } from '@/components/recommendation-card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { ChatResponse } from '@/types'

type ChatItem =
  | { id: string; role: 'user'; text: string }
  | {
      id: string
      role: 'assistant'
      text: string
      recommendation: ChatResponse['recommendation']
    }

const EXAMPLES = [
  '오늘 가슴 운동 루틴 짜줘',
  '30분 짜리 가벼운 러닝 추천해줘',
  '최근 기록 보고 내일 뭐 하면 좋을지 알려줘',
]

export default function ChatPage() {
  const router = useRouter()
  const [items, setItems] = useState<ChatItem[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items, loading])

  async function send(message: string) {
    const text = message.trim()
    if (!text || loading) return

    setError(null)
    setInput('')
    setItems((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', text }])
    setLoading(true)

    const token = await getAccessToken()
    if (!token) {
      router.replace('/login')
      return
    }

    try {
      const res = await apiClient.post<ChatResponse>('/chat', { message: text }, token)
      setItems((prev) => [
        ...prev,
        {
          id: res.message_id,
          role: 'assistant',
          text: res.response_text,
          recommendation: res.recommendation,
        },
      ])
    } catch {
      setError('답변을 받지 못했습니다. 잠시 후 다시 시도해주세요.')
    }
    setLoading(false)
  }

  function applyRecommendation(rec: NonNullable<ChatResponse['recommendation']>) {
    setWorkoutPrefill({
      workout_type: rec.workout_type,
      structured_data: rec.structured_data,
    })
    router.push('/workouts/new')
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    send(input)
  }

  return (
    <main className="mx-auto flex h-screen max-w-lg flex-col p-4">
      <header className="mb-3 flex shrink-0 items-center justify-between">
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
          ← 대시보드
        </Link>
        <h1 className="text-base font-bold">AI 코치</h1>
        <span className="w-16" />
      </header>

      <div className="flex-1 overflow-y-auto">
        {items.length === 0 && !loading ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <p className="text-sm text-muted-foreground">
              운동 목표나 오늘 컨디션을 말해보세요.
              <br />
              프로필과 최근 기록을 바탕으로 루틴을 추천해드려요.
            </p>
            <div className="flex flex-col gap-2">
              {EXAMPLES.map((ex) => (
                <Button
                  key={ex}
                  variant="outline"
                  size="sm"
                  onClick={() => send(ex)}
                  className="h-auto whitespace-normal py-2"
                >
                  {ex}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-4 pb-2">
            {items.map((item) =>
              item.role === 'user' ? (
                <div key={item.id} className="self-end max-w-[85%]">
                  <div className="rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm text-primary-foreground">
                    {item.text}
                  </div>
                </div>
              ) : (
                <div key={item.id} className="self-start max-w-[90%]">
                  <div className="rounded-2xl rounded-bl-sm bg-muted px-4 py-2 text-sm whitespace-pre-wrap">
                    {item.text}
                  </div>
                  {item.recommendation && (
                    <RecommendationCard
                      workoutType={item.recommendation.workout_type}
                      data={item.recommendation.structured_data}
                      onApply={() => applyRecommendation(item.recommendation!)}
                    />
                  )}
                </div>
              )
            )}
            {loading && (
              <div className="self-start">
                <div className="rounded-2xl rounded-bl-sm bg-muted px-4 py-2 text-sm text-muted-foreground">
                  코치가 생각 중...
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && <p className="mt-2 shrink-0 text-center text-sm text-destructive">{error}</p>}

      <form onSubmit={handleSubmit} className="mt-3 flex shrink-0 items-end gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(input)
            }
          }}
          placeholder="메시지를 입력하세요 (Enter 전송 · Shift+Enter 줄바꿈)"
          rows={1}
          className="max-h-32 min-h-9 flex-1 resize-none"
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !input.trim()} size="lg">
          전송
        </Button>
      </form>
    </main>
  )
}
