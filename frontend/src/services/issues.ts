export interface SubCausa {
  id: number
  descripcion: string
}

export interface CausaRaiz {
  id: number
  categoria: string
  descripcion: string
  subcausas: SubCausa[]
}

export interface IshikawaData {
  id: number
  issue: number
  categorias: Record<string, CausaRaiz[]>
}

export interface TransitionHistoryEntry {
  id: number
  estado_anterior: string
  estado_nuevo: string
  usuario: number
  timestamp: string
  comentario: string
}

export interface IssueListItem {
  id: number
  tipo: string
  titulo: string
  area: string
  gravedad: string
  estado: string
  reportado_por: number
  fecha_evento: string
  created_at: string
}

export interface IssueDetail extends Omit<IssueListItem, 'reportado_por'> {
  descripcion: string
  updated_at: string
  reportado_por: { id: number; nombre_completo: string } | number
  ishikawa: IshikawaData | null
  historial_estados: TransitionHistoryEntry[]
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface IssueFilters {
  tipo?: string
  estado?: string
  gravedad?: string
  area?: string
  fecha_evento__gte?: string
  fecha_evento__lte?: string
  page?: number
}

export interface IssueWriteData {
  tipo: string
  titulo: string
  descripcion: string
  fecha_evento: string
  area: string
  gravedad: string
}

export interface IshikawaCausaWrite {
  categoria: string
  descripcion: string
  subcausas: Array<{ descripcion: string }>
}

export interface IshikawaWriteData {
  causas: IshikawaCausaWrite[]
}

import { fetchWithAuth, handleResponse } from './fetchWithAuth'

export const issuesService = {
  async getIssues(filters: IssueFilters = {}): Promise<PaginatedResponse<IssueListItem>> {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined && v !== '' && v !== null) params.set(k, String(v))
    }
    const qs = params.toString()
    const resp = await fetchWithAuth(`/api/issues/${qs ? `?${qs}` : ''}`)
    return handleResponse(resp)
  },

  async getIssue(id: number): Promise<IssueDetail> {
    const resp = await fetchWithAuth(`/api/issues/${id}/`)
    return handleResponse(resp)
  },

  async createIssue(data: IssueWriteData): Promise<IssueDetail> {
    const resp = await fetchWithAuth('/api/issues/', { method: 'POST', body: JSON.stringify(data) })
    return handleResponse(resp)
  },

  async updateIssue(id: number, data: Partial<IssueWriteData>): Promise<IssueDetail> {
    const resp = await fetchWithAuth(`/api/issues/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
    return handleResponse(resp)
  },

  async transitionIssue(id: number, estado: string, comentario = ''): Promise<IssueDetail> {
    const resp = await fetchWithAuth(`/api/issues/${id}/transition/`, {
      method: 'POST',
      body: JSON.stringify({ estado, comentario }),
    })
    return handleResponse(resp)
  },

  async getIshikawa(id: number): Promise<IshikawaData> {
    const resp = await fetchWithAuth(`/api/issues/${id}/ishikawa/`)
    return handleResponse(resp)
  },

  async updateIshikawa(id: number, data: IshikawaWriteData): Promise<IshikawaData> {
    const resp = await fetchWithAuth(`/api/issues/${id}/ishikawa/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return handleResponse(resp)
  },
}
