import { fetchWithAuth, handleResponse } from './fetchWithAuth'

export interface ActividadItem {
  id: number
  descripcion: string
  responsable: number
  responsable_nombre: string
  fecha_limite: string
  estado: 'pendiente' | 'en_proceso' | 'completada'
  created_at: string
}

export interface EvidenciaItem {
  id: number
  nombre_original: string
  content_type: string
  tamaño_bytes: number
  uploaded_by: number
  uploaded_at: string
}

export interface PlanDetalle {
  id: number
  accion: number
  progreso: number
  actividades: ActividadItem[]
  created_at: string
  updated_at: string
}

export interface PlanResumen {
  id: number
  accion: number
  progreso: number
  created_at: string
  updated_at: string
}

const BASE = '/api'

export const planesService = {
  async getPlanes(): Promise<PlanResumen[]> {
    const r = await fetchWithAuth(`${BASE}/planes/`)
    return handleResponse(r)
  },

  async getPlan(planId: number): Promise<PlanDetalle> {
    const r = await fetchWithAuth(`${BASE}/planes/${planId}/`)
    return handleResponse(r)
  },

  async getPlanByAccion(accionId: number): Promise<PlanDetalle | null> {
    const planes = await planesService.getPlanes()
    const match = planes.find((p) => p.accion === accionId)
    if (!match) return null
    return planesService.getPlan(match.id)
  },

  async createPlan(accionId: number, actividades: { descripcion: string; responsable: number; fecha_limite: string }[]): Promise<PlanDetalle> {
    const r = await fetchWithAuth(`${BASE}/planes/`, {
      method: 'POST',
      body: JSON.stringify({ accion: accionId, actividades }),
    })
    return handleResponse(r)
  },

  async addActividad(planId: number, data: { descripcion: string; responsable: number; fecha_limite: string }): Promise<ActividadItem> {
    const r = await fetchWithAuth(`${BASE}/actividades/`, {
      method: 'POST',
      body: JSON.stringify({ plan: planId, ...data }),
    })
    return handleResponse(r)
  },

  async updateActividad(actividadId: number, data: Partial<{ descripcion: string; responsable: number; fecha_limite: string }>): Promise<ActividadItem> {
    const r = await fetchWithAuth(`${BASE}/actividades/${actividadId}/`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    return handleResponse(r)
  },

  async deleteActividad(actividadId: number): Promise<void> {
    const r = await fetchWithAuth(`${BASE}/actividades/${actividadId}/`, { method: 'DELETE' })
    if (!r.ok) {
      const body = await r.json().catch(() => ({ detail: r.statusText }))
      throw Object.assign(new Error(body.detail ?? 'Error'), { status: r.status, data: body })
    }
  },

  async transitionActividad(actividadId: number, estado: string): Promise<ActividadItem> {
    const r = await fetchWithAuth(`${BASE}/actividades/${actividadId}/transition/`, {
      method: 'POST',
      body: JSON.stringify({ estado }),
    })
    return handleResponse(r)
  },

  async getEvidencias(actividadId: number): Promise<EvidenciaItem[]> {
    const r = await fetchWithAuth(`${BASE}/actividades/${actividadId}/evidencias/`)
    return handleResponse(r)
  },

  async uploadEvidencia(actividadId: number, file: File): Promise<EvidenciaItem> {
    const formData = new FormData()
    formData.append('archivo', file)
    const r = await fetchWithAuth(`${BASE}/actividades/${actividadId}/evidencias/upload/`, {
      method: 'POST',
      body: formData,
      headers: {},
    })
    return handleResponse(r)
  },

  async deleteEvidencia(evidenciaId: number): Promise<void> {
    const r = await fetchWithAuth(`${BASE}/evidencias/${evidenciaId}/`, { method: 'DELETE' })
    if (!r.ok) {
      const body = await r.json().catch(() => ({ detail: r.statusText }))
      throw Object.assign(new Error(body.detail ?? 'Error'), { status: r.status, data: body })
    }
  },

  async getSignedUrl(evidenciaId: number): Promise<{ url: string; expires_at: string }> {
    const r = await fetchWithAuth(`${BASE}/evidencias/${evidenciaId}/signed-url/`)
    return handleResponse(r)
  },
}
