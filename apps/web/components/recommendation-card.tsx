'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { WORKOUT_TYPE_META } from '@/lib/constants'
import type { Recommendation, WorkoutType } from '@/types'

interface Props {
  workoutType: WorkoutType
  data: Recommendation
  onApply: () => void
}

export function RecommendationCard({ workoutType, data, onApply }: Props) {
  const meta = WORKOUT_TYPE_META[workoutType]

  return (
    <Card className="mt-3 rounded-xl border border-border bg-card shadow-sm ring-0">
      <CardHeader className="gap-2 border-b border-border/70 px-5 pb-1 pt-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className={`rounded-full ${meta.badge}`}>
            {meta.label}
          </Badge>
          {'estimated_duration_minutes' in data && data.estimated_duration_minutes != null && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              약 {data.estimated_duration_minutes}분
            </span>
          )}
          {'total_duration_minutes' in data && (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              약 {data.total_duration_minutes}분
            </span>
          )}
        </div>
        <CardTitle className="text-lg font-semibold">{data.title}</CardTitle>
      </CardHeader>

      <CardContent className="flex flex-col gap-2 px-5 pt-2">
        {data.type === 'weight' && (
          <>
            <p className="text-xs font-medium text-muted-foreground">
              타겟: {data.muscle_group}
            </p>
            <ul className="flex flex-col gap-2">
              {data.exercises.map((ex, i) => (
                <li key={i} className="rounded-lg border border-border/70 bg-muted/40 p-3">
                  <p className="text-sm font-medium">{ex.name}</p>
                  <ul className="mt-2 grid gap-1 text-sm">
                    {ex.sets.map((s, si) => (
                      <li
                        key={si}
                        className="grid grid-cols-[2.75rem_1fr] items-center gap-1.5 rounded-md bg-background px-2 py-0.5 leading-tight"
                      >
                        <span className="text-xs font-medium text-muted-foreground">
                          {si + 1}세트
                        </span>
                        <span className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                          <span className="font-medium">
                            {s.weight_kg != null ? `${s.weight_kg}kg` : '-'} ×{' '}
                            {s.reps != null ? `${s.reps}회` : '-'}
                          </span>
                          {s.rest_seconds != null && (
                            <span className="text-xs text-muted-foreground">
                              휴식 {s.rest_seconds}초
                            </span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {ex.notes && <p className="mt-2 text-xs text-muted-foreground">{ex.notes}</p>}
                </li>
              ))}
            </ul>
          </>
        )}

        {data.type === 'running' && (
          <dl className="grid gap-3 text-sm">
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-border/70 bg-muted/40 p-3">
                <dt className="text-xs text-muted-foreground">거리</dt>
                <dd className="mt-1 font-semibold">{data.distance_km}km</dd>
              </div>
              <div className="rounded-lg border border-border/70 bg-muted/40 p-3">
                <dt className="text-xs text-muted-foreground">평균 페이스</dt>
                <dd className="mt-1 font-semibold">{data.avg_pace}</dd>
              </div>
            </div>
            {[
              ['웜업', data.warmup],
              ['본운동', data.main],
              ['쿨다운', data.cooldown],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border/70 bg-muted/40 p-3">
                <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
                <dd className="mt-1 leading-relaxed">{value}</dd>
              </div>
            ))}
          </dl>
        )}

        {data.type === 'other' && (
          <p className="whitespace-pre-wrap rounded-lg border border-border/70 bg-muted/40 p-3 text-sm leading-relaxed">
            {data.content}
          </p>
        )}

        {data.cautions && (
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-800">
            ⚠️ {data.cautions}
          </p>
        )}

        <Button onClick={onApply} size="lg" className="mb-2  w-full">
          이 루틴으로 기록하기
        </Button>
      </CardContent>
    </Card>
  )
}
