export interface TokenPayload {
  user_id: number
  email?: string
  role: string
  tenant: string
  exp: number
  iat?: number
}

export interface AuthUser {
  id: number
  email: string
  role: string
  tenant: string
}

const KEYS = {
  access: 'access_token',
  refresh: 'refresh_token',
} as const

// --- Token storage ---

export function saveTokens(access: string, refresh: string): void {
  localStorage.setItem(KEYS.access, access)
  localStorage.setItem(KEYS.refresh, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(KEYS.access)
  localStorage.removeItem(KEYS.refresh)
}

export function getAccessToken(): string | null {
  return localStorage.getItem(KEYS.access)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(KEYS.refresh)
}

// --- JWT decode (no external library needed) ---

export function decodeToken(token: string): TokenPayload | null {
  try {
    const [, payload] = token.split('.')
    const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json) as TokenPayload
  } catch {
    return null
  }
}

export function isTokenValid(): boolean {
  const token = getAccessToken()
  if (!token) return false
  const payload = decodeToken(token)
  if (!payload) return false
  return payload.exp > Date.now() / 1000
}

export function getUserFromToken(): AuthUser | null {
  const token = getAccessToken()
  if (!token) return null
  const payload = decodeToken(token)
  if (!payload) return null
  return {
    id: payload.user_id,
    email: payload.email ?? '',
    role: payload.role,
    tenant: payload.tenant,
  }
}

// --- API calls ---

export async function loginApi(
  email: string,
  password: string,
): Promise<{ access: string; refresh: string }> {
  const resp = await fetch('/api/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    const err = Object.assign(new Error(body.detail ?? 'Error de autenticación'), {
      status: resp.status,
    })
    throw err
  }
  return resp.json()
}

export async function logoutApi(refresh: string): Promise<void> {
  await fetch('/api/auth/logout/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  }).catch(() => {
    // Best-effort: even if the server fails, clear tokens locally
  })
}
