import { createClient } from '@/lib/supabase/client'

// FastAPI 호출에 쓸 Supabase 액세스 토큰을 가져온다. 미로그인 시 null.
export async function getAccessToken(): Promise<string | null> {
  const supabase = createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  return session?.access_token ?? null
}
