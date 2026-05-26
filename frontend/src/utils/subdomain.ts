const BASE = import.meta.env.TENANT_BASE_DOMAIN ?? 'sgca.com'

export function getSubdomain(): string | null {
  const hostname = window.location.hostname
  if (hostname === BASE) return null
  if (hostname.endsWith(`.${BASE}`)) return hostname.slice(0, -(BASE.length + 1))
  return null
}

export function getRootUrl(): string {
  const { protocol, port } = window.location
  const portStr = port ? `:${port}` : ''
  return `${protocol}//${BASE}${portStr}/`
}
