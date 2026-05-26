import type { PaginatedResponse } from './issues'

export interface UserBasic {
  id: number
  nombre_completo: string
  email: string
}

export interface IssueBasic {
  id: number
  titulo: string
  tipo: string
  estado: string
}

export interface HistorialEstadoEntry {
  id: number
  estado_anterior: string
  estado_nuevo: string
  usuario: number
  timestamp: string
  comentario: string
}

export interface UserBasicNullable {
  id: number
  nombre_completo: string
}

export interface AccionListItem {
  id: number
  issue: IssueBasic
  tipo: string
  resultado_esperado_resumen: string
  responsable: UserBasic
  responsable_temporal: UserBasicNullable | null
  responsable_temporal_hasta: string | null
  fecha_limite: string
  estado: string
  created_at: string
}

export interface AccionDetail {
  id: number
  issue: IssueBasic
  tipo: string
  resultado_esperado: string
  responsable: UserBasic
  responsable_temporal: UserBasicNullable | null
  responsable_temporal_hasta: string | null
  fecha_limite: string
  estado: string
  created_by: number
  created_at: string
  updated_at: string
  historial_estados?: HistorialEstadoEntry[]
}

export interface AccionWriteData {
  issue_id: number
  tipo: string
  resultado_esperado: string
  responsable_id: number
  fecha_limite: string
}

export interface AccionFilters {
  estado?: string
  tipo?: string
  responsable?: number
  fecha_limite__gte?: string
  fecha_limite__lte?: string
  page?: number
}

import { fetchWithAuth, handleResponse } from './fetchWithAuth'

export const accionesService = {
  async listAcciones(filters: AccionFilters = {}): Promise<PaginatedResponse<AccionListItem>> {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(filters)) {
      if (v !== undefined && v !== '' && v !== null) params.set(k, String(v))
    }
    const qs = params.toString()
    const resp = await fetchWithAuth(`/api/acciones/${qs ? `?${qs}` : ''}`)
    return handleResponse(resp)
  },

  async getAccion(id: number): Promise<AccionDetail> {
    const resp = await fetchWithAuth(`/api/acciones/${id}/`)
    return handleResponse(resp)
  },

  async createAccion(data: AccionWriteData): Promise<AccionDetail> {
    const resp = await fetchWithAuth('/api/acciones/', { method: 'POST', body: JSON.stringify(data) })
    return handleResponse(resp)
  },

  async updateAccion(id: number, data: Partial<AccionWriteData>): Promise<AccionDetail> {
    const resp = await fetchWithAuth(`/api/acciones/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })
    return handleResponse(resp)
  },

  async transitionAccion(id: number, estado: string, comentario = ''): Promise<AccionDetail> {
    const resp = await fetchWithAuth(`/api/acciones/${id}/transition/`, {
      method: 'POST',
      body: JSON.stringify({ estado, comentario }),
    })
    return handleResponse(resp)
  },

  async getHistorial(id: number): Promise<HistorialEstadoEntry[]> {
    const resp = await fetchWithAuth(`/api/acciones/${id}/historial/`)
    return handleResponse(resp)
  },

  async assignResponsableTemporal(
    id: number,
    data: { responsable_temporal_id: number; responsable_temporal_hasta: string },
  ): Promise<AccionDetail> {
    const resp = await fetchWithAuth(`/api/acciones/${id}/responsable-temporal/`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
    return handleResponse(resp)
  },

  async removeResponsableTemporal(id: number): Promise<AccionDetail> {
    const resp = await fetchWithAuth(`/api/acciones/${id}/responsable-temporal/`, {
      method: 'DELETE',
    })
    return handleResponse(resp)
  },
}
