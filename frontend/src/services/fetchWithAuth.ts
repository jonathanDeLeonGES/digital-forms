import { getAccessToken, getRefreshToken, saveTokens, clearTokens, refreshTokenApi } from './auth'

export async function fetchWithAuth(input: string, init: RequestInit = {}): Promise<Response> {
  const makeHeaders = (token: string | null): HeadersInit => ({
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init.headers as Record<string, string> ?? {}),
  })

  const resp = await fetch(input, { ...init, headers: makeHeaders(getAccessToken()) })

  if (resp.status !== 401) return resp

  const refresh = getRefreshToken()
  if (!refresh) {
    clearTokens()
    window.location.href = '/login'
    return resp
  }

  try {
    const newAccess = await refreshTokenApi(refresh)
    saveTokens(newAccess, refresh)
    return fetch(input, { ...init, headers: makeHeaders(newAccess) })
  } catch {
    clearTokens()
    window.location.href = '/login'
    return resp
  }
}

export async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    const err = Object.assign(new Error(body.detail ?? JSON.stringify(body)), {
      status: resp.status,
      data: body,
    })
    throw err
  }
  return resp.json()
}
