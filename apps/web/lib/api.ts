const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...fetchOptions } = options
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...fetchOptions.headers,
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...fetchOptions, headers })

  if (!res.ok) {
    let message = `API error: ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) message = body.detail
    } catch {
      // 응답 본문이 JSON이 아니면 기본 메시지 사용
    }
    throw new ApiError(res.status, message)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const apiClient = {
  get: <T>(path: string, token?: string) =>
    apiFetch<T>(path, { method: 'GET', token }),

  post: <T>(path: string, body: unknown, token?: string) =>
    apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body), token }),

  put: <T>(path: string, body: unknown, token?: string) =>
    apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body), token }),

  delete: <T>(path: string, token?: string) =>
    apiFetch<T>(path, { method: 'DELETE', token }),
}
