'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Send, Settings } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { getAccessToken } from '@/lib/auth'
import { setWorkoutPrefill } from '@/lib/workout-prefill'
import { PERSONAS } from '@/lib/constants'
import { RecommendationCard } from '@/components/recommendation-card'
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ChatResponse, Persona, Recommendation, UserProfile, WorkoutType } from '@/types'

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

const LOADING_MESSAGES = [
  '코치가 최근 기록을 살펴보고 있어요',
  '오늘 컨디션에 맞는 방향을 잡는 중이에요',
  '운동 강도와 휴식 시간을 조율하고 있어요',
  '곧 루틴이 완성돼요',
]

const WORKOUT_TYPES = new Set<WorkoutType>(['weight', 'running', 'other'])

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isJsonLikeText(text: string) {
  const trimmed = text.trim()
  return trimmed.startsWith('{') || trimmed.startsWith('```') || trimmed.includes('"structured_data"')
}

function parseJsonObject(text: string): Record<string, unknown> | null {
  const trimmed = text.trim()
  const unfenced = trimmed.startsWith('```')
    ? trimmed.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '').trim()
    : trimmed

  try {
    const parsed = JSON.parse(unfenced)
    return isRecord(parsed) ? parsed : null
  } catch {
    const start = unfenced.indexOf('{')
    const end = unfenced.lastIndexOf('}')
    if (start === -1 || end <= start) return null
    try {
      const parsed = JSON.parse(unfenced.slice(start, end + 1))
      return isRecord(parsed) ? parsed : null
    } catch {
      return null
    }
  }
}

function isWorkoutType(value: unknown): value is WorkoutType {
  return typeof value === 'string' && WORKOUT_TYPES.has(value as WorkoutType)
}

function fallbackRecommendationText(data: Recommendation) {
  return `${data.title} 루틴을 준비했어요. 아래 카드에서 확인하고 바로 기록할 수 있어요.`
}

function normalizeChatResponse(res: ChatResponse): ChatResponse {
  const parsed = parseJsonObject(res.response_text)
  if (!parsed) {
    return isJsonLikeText(res.response_text)
      ? {
          ...res,
          response_text:
            '루틴 응답 형식이 중간에 깨졌어요. 같은 요청을 한 번만 다시 보내주시면 카드 형태로 다시 만들어드릴게요.',
        }
      : res
  }

  const recommendation = isRecord(parsed.recommendation) ? parsed.recommendation : null
  const workoutType = recommendation
    ? recommendation.workout_type
    : parsed.workout_type ?? parsed.type
  const structuredData = recommendation
    ? recommendation.structured_data
    : parsed.structured_data ?? (isWorkoutType(parsed.type) ? parsed : null)

  if (!isWorkoutType(workoutType) || !isRecord(structuredData)) {
    return res
  }

  const typedStructuredData = structuredData as unknown as Recommendation
  const responseText =
    typeof parsed.response_text === 'string' && !parseJsonObject(parsed.response_text)
      ? parsed.response_text
      : fallbackRecommendationText(typedStructuredData)

  return {
    ...res,
    response_text: responseText,
    recommendation: res.recommendation ?? {
      // 프런트엔드에서만 복구한 추천은 DB에 저장된 추천 ID가 없다.
      id: null,
      workout_type: workoutType,
      structured_data: typedStructuredData,
    },
  }
}

export default function ChatPage() {
  const router = useRouter()
  const [items, setItems] = useState<ChatItem[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 코치(페르소나) 설정
  const [persona, setPersona] = useState<Persona | null>(null)
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [savingPersona, setSavingPersona] = useState(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items, loading])

  useEffect(() => {
    if (!loading) {
      setLoadingStep(0)
      return
    }

    setLoadingStep(0)
    const timer = window.setInterval(() => {
      setLoadingStep((prev) => Math.min(prev + 1, LOADING_MESSAGES.length - 1))
    }, 2200)

    return () => window.clearInterval(timer)
  }, [loading])

  // 현재 페르소나 로드 (설정 다이얼로그 표시용)
  useEffect(() => {
    async function loadPersona() {
      const token = await getAccessToken()
      if (!token) return
      try {
        const profile = await apiClient.get<UserProfile>('/profile', token)
        setPersona(profile.persona)
      } catch {
        // 프로필 조회 실패해도 챗봇 사용에는 지장 없음
      }
    }
    loadPersona()
  }, [])

  // 다이얼로그 열 때 현재 페르소나를 선택값으로 초기화
  function openSettings() {
    setSelectedPersona(persona)
    setSettingsOpen(true)
  }

  async function savePersona() {
    if (!selectedPersona || selectedPersona === persona || savingPersona) {
      setSettingsOpen(false)
      return
    }
    setSavingPersona(true)
    const token = await getAccessToken()
    if (!token) {
      router.replace('/login')
      return
    }
    try {
      await apiClient.put('/profile', { persona: selectedPersona }, token)
      setPersona(selectedPersona)
      setSettingsOpen(false)
    } catch {
      setError('코치 변경에 실패했습니다.')
    }
    setSavingPersona(false)
  }

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
      const res = normalizeChatResponse(
        await apiClient.post<ChatResponse>('/chat', { message: text }, token)
      )
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
      ai_recommendation_id: rec.id,
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
        <Link
          href="/dashboard"
          aria-label="대시보드로 이동"
          className={cn(buttonVariants({ variant: 'outline', size: 'icon-sm' }))}
        >
          <ArrowLeft aria-hidden="true" />
        </Link>
        <h1 className="text-base font-bold">내 핏피티 코치</h1>
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="icon-sm"
            onClick={openSettings}
            aria-label="코치 설정"
          >
            <Settings />
          </Button>
        </div>
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
              <div className="self-start max-w-[90%]">
                <div className="flex items-center gap-3 rounded-2xl rounded-bl-sm bg-muted px-4 py-3 text-sm text-muted-foreground">
                  <span
                    className="flex h-6 w-9 shrink-0 items-center justify-center gap-1 rounded-full bg-white shadow-sm ring-1 ring-gray-200"
                    aria-hidden="true"
                  >
                    {[0, 1, 2].map((dot) => (
                      <span
                        key={dot}
                        className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-500"
                        style={{ animationDelay: `${dot * 140}ms` }}
                      />
                    ))}
                  </span>
                  <span>{LOADING_MESSAGES[loadingStep]}</span>
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
          <Send data-icon="inline-start" aria-hidden="true" />
          전송
        </Button>
      </form>

      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>코치 설정</DialogTitle>
            <DialogDescription>대화 상대(트레이너 페르소나)를 선택하세요.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            {PERSONAS.map((p) => {
              const selected = selectedPersona === p.code
              return (
                <button
                  key={p.code}
                  type="button"
                  disabled={savingPersona}
                  onClick={() => setSelectedPersona(p.code)}
                  aria-pressed={selected}
                  className={`rounded-xl border px-4 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 ${
                    selected
                      ? 'border-foreground bg-muted'
                      : 'border-border hover:border-foreground/40'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{p.name}</span>
                    {persona === p.code && (
                      <span className="text-xs text-muted-foreground">현재</span>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{p.description}</p>
                </button>
              )
            })}
          </div>
          <DialogFooter>
            <DialogClose
              render={<Button variant="outline" disabled={savingPersona} />}
            >
              취소
            </DialogClose>
            <Button
              onClick={savePersona}
              disabled={savingPersona || !selectedPersona}
            >
              {savingPersona ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  )
}
