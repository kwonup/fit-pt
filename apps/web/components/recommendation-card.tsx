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
    <Card className="mt-2">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className={meta.badge}>
            {meta.label}
          </Badge>
          {'estimated_duration_minutes' in data && data.estimated_duration_minutes != null && (
            <span className="text-xs text-muted-foreground">
              약 {data.estimated_duration_minutes}분
            </span>
          )}
          {'total_duration_minutes' in data && (
            <span className="text-xs text-muted-foreground">
              약 {data.total_duration_minutes}분
            </span>
          )}
        </div>
        <CardTitle>{data.title}</CardTitle>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {data.type === 'weight' && (
          <>
            <p className="text-xs text-muted-foreground">타겟: {data.muscle_group}</p>
            <ul className="flex flex-col gap-2">
              {data.exercises.map((ex, i) => (
                <li key={i} className="rounded-lg ring-1 ring-foreground/10 p-3">
                  <p className="text-sm font-medium">{ex.name}</p>
                  <ul className="mt-1 flex flex-col gap-0.5 text-sm text-muted-foreground">
                    {ex.sets.map((s, si) => (
                      <li key={si} className="flex gap-3">
                        <span className="w-12 shrink-0">{si + 1}세트</span>
                        <span>
                          {s.weight_kg != null ? `${s.weight_kg}kg` : '-'} ×{' '}
                          {s.reps != null ? `${s.reps}회` : '-'}
                          {s.rest_seconds != null ? ` · 휴식 ${s.rest_seconds}초` : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {ex.notes && <p className="mt-1 text-xs text-muted-foreground">{ex.notes}</p>}
                </li>
              ))}
            </ul>
          </>
        )}

        {data.type === 'running' && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted-foreground">거리</dt>
            <dd>{data.distance_km}km</dd>
            <dt className="text-muted-foreground">평균 페이스</dt>
            <dd>{data.avg_pace}</dd>
            <dt className="text-muted-foreground">웜업</dt>
            <dd>{data.warmup}</dd>
            <dt className="text-muted-foreground">본운동</dt>
            <dd>{data.main}</dd>
            <dt className="text-muted-foreground">쿨다운</dt>
            <dd>{data.cooldown}</dd>
          </dl>
        )}

        {data.type === 'other' && (
          <p className="whitespace-pre-wrap text-sm">{data.content}</p>
        )}

        {data.cautions && (
          <p className="rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
            ⚠️ {data.cautions}
          </p>
        )}

        <Button onClick={onApply} className="self-start">
          이 루틴으로 기록하기
        </Button>
      </CardContent>
    </Card>
  )
}
