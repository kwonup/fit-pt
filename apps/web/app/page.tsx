import Link from 'next/link'
import { buttonVariants } from '@/components/ui/button'

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="text-4xl font-bold">핏피티 (Fit PT)</h1>
        <p className="max-w-md text-muted-foreground">
          AI 챗봇이 운동 기록을 분석하고 오늘의 루틴을 추천합니다. 추천을 한 번의 클릭으로 실제
          운동 기록으로 남겨보세요.
        </p>
      </div>
      <Link href="/login" className={buttonVariants({ size: 'lg' })}>
        시작하기
      </Link>
    </main>
  )
}