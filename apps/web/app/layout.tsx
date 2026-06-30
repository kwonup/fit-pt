import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '핏피티 (Fit PT)',
  description: 'AI 챗봇이 운동 기록을 분석하고 맞춤 루틴을 추천하는 웹 서비스',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}
