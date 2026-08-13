import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { BrandLogo } from '@/components/brand-logo'

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-7 bg-gradient-to-b from-white to-blue-50/50 p-8">
      <div className="flex flex-col items-center text-center">
        <BrandLogo />
        <h1 className="sr-only">핏피티 (Fit PT)</h1>
        <p className="max-w-md text-gray-500">
          AI 챗봇이 운동 기록을 분석하고 오늘의 루틴을 추천합니다.
          추천을 한 번의 클릭으로 실제 운동 기록으로 남겨보세요.
        </p>
      </div>
      <Link
        href="/login"
        className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gray-900 px-6 text-sm font-semibold text-white shadow-sm transition-all hover:bg-gray-700 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 active:translate-y-px"
      >
        시작하기
        <ArrowRight data-icon="inline-end" aria-hidden="true" />
      </Link>
    </main>
  )
}
