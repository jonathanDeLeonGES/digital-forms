import { useState } from 'react'
import { type ActividadItem, type EvidenciaItem, planesService } from '../../services/planes'
import { ActividadStatusBadge } from './ActividadStatusBadge'
import { EvidenciaUploader } from './EvidenciaUploader'

const NEXT_ESTADO: Record<string, string[]> = {
  pendiente:  ['en_proceso'],
  en_proceso: ['completada', 'pendiente'],
  completada: ['en_proceso'],
}

const ESTADO_LABEL: Record<string, string> = {
  pendiente: 'Pendiente',
  en_proceso: 'En Proceso',
  completada: 'Completada',
}

interface Props {
  actividad: ActividadItem
  userRole: string
  userId: number
  onChanged: () => void
  canManage: boolean
}

export function ActividadCard({ actividad, userRole, userId, onChanged, canManage }: Props) {
  const [evidencias, setEvidencias] = useState<EvidenciaItem[] | null>(null)
  const [showEvidencias, setShowEvidencias] = useState(false)
  const [transitioning, setTransitioning] = useState(false)
  const [error, setError] = useState('')

  const isOwner = actividad.responsable === userId
  const canTransition = canManage || isOwner

  async function loadEvidencias() {
    const list = await planesService.getEvidencias(actividad.id)
    setEvidencias(list)
  }

  async function toggleEvidencias() {
    if (!showEvidencias && evidencias === null) await loadEvidencias()
    setShowEvidencias((v) => !v)
  }

  async function handleTransition(nuevoEstado: string) {
    setTransitioning(true)
    setError('')
    try {
      await planesService.transitionActividad(actividad.id, nuevoEstado)
      onChanged()
    } catch (err: unknown) {
      const e = err as { data?: { detail?: string }; message?: string }
      setError(e?.data?.detail ?? e?.message ?? 'Error al cambiar estado.')
    } finally {
      setTransitioning(false)
    }
  }

  async function handleUpload(file: File) {
    await planesService.uploadEvidencia(actividad.id, file)
    await loadEvidencias()
  }

  async function handleDeleteEvidencia(evId: number) {
    await planesService.deleteEvidencia(evId)
    setEvidencias((prev) => prev?.filter((e) => e.id !== evId) ?? null)
  }

  async function handleOpenEvidencia(evId: number) {
    const { url } = await planesService.getSignedUrl(evId)
    window.open(url, '_blank', 'noopener')
  }

  const nextStates = canTransition ? (NEXT_ESTADO[actividad.estado] ?? []) : []

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <ActividadStatusBadge estado={actividad.estado} />
            <span className="text-sm font-medium text-gray-900 truncate">{actividad.descripcion}</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Responsable: <span className="font-medium">{actividad.responsable_nombre}</span>
            {' · '}
            Fecha límite: <span className="font-medium">{actividad.fecha_limite}</span>
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {nextStates.map((s) => (
            <button
              key={s}
              disabled={transitioning}
              onClick={() => handleTransition(s)}
              className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 disabled:opacity-50 border border-blue-200"
            >
              → {ESTADO_LABEL[s]}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      <div className="mt-3 border-t border-gray-100 pt-3">
        <div className="flex items-center justify-between">
          <button
            onClick={toggleEvidencias}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            {showEvidencias ? 'Ocultar evidencias' : 'Ver evidencias'}
          </button>
          {(isOwner || canManage) && (
            <EvidenciaUploader onUpload={handleUpload} />
          )}
        </div>

        {showEvidencias && (
          <ul className="mt-2 space-y-1">
            {evidencias?.length === 0 && (
              <li className="text-xs text-gray-400">Sin evidencias.</li>
            )}
            {evidencias?.map((ev) => (
              <li key={ev.id} className="flex items-center justify-between text-xs text-gray-700 py-0.5">
                <button
                  onClick={() => handleOpenEvidencia(ev.id)}
                  className="hover:underline text-blue-600 truncate max-w-[200px]"
                >
                  {ev.nombre_original}
                </button>
                {canManage && (
                  <button
                    onClick={() => handleDeleteEvidencia(ev.id)}
                    className="ml-2 text-red-400 hover:text-red-600"
                  >
                    ✕
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
