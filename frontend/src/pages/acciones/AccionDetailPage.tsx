import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { accionesService, type AccionDetail, type HistorialEstadoEntry } from '../../services/acciones'
import { AccionStatusBadge } from '../../components/acciones/AccionStatusBadge'
import { useAuth } from '../../context/AuthContext'

const TIPO_LABELS: Record<string, string> = {
  correctiva: 'Correctiva',
  preventiva: 'Preventiva',
  mejora: 'De Mejora',
}

const ESTADO_LABELS: Record<string, string> = {
  abierto: 'Abierto',
  en_proceso: 'En Proceso',
  cerrado: 'Cerrado',
  verificado: 'Verificado',
}

function canTransition(role: string, accionResponsableId: number, userId: number, currentEstado: string): string | null {
  if (role === 'admin') {
    if (currentEstado === 'abierto') return 'en_proceso'
    if (currentEstado === 'en_proceso') return 'cerrado'
    if (currentEstado === 'cerrado') return 'verificado'
    return null
  }
  if (role === 'responsable' && accionResponsableId === userId && currentEstado === 'abierto') return 'en_proceso'
  if (role === 'supervisor' && currentEstado === 'en_proceso') return 'cerrado'
  if (role === 'verificador' && currentEstado === 'cerrado') return 'verificado'
  return null
}

interface TransitionModalProps {
  nextEstado: string
  onConfirm: (comentario: string) => void
  onClose: () => void
  loading: boolean
}

function TransitionModal({ nextEstado, onConfirm, onClose, loading }: TransitionModalProps) {
  const [comentario, setComentario] = useState('')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Mover a &ldquo;{ESTADO_LABELS[nextEstado] ?? nextEstado}&rdquo;
        </h3>
        <p className="text-sm text-gray-500 mb-4">Puede agregar un comentario opcional.</p>
        <textarea
          value={comentario}
          onChange={(e) => setComentario(e.target.value)}
          placeholder="Comentario (opcional)"
          rows={3}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
        />
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            onClick={() => onConfirm(comentario)}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Guardando...' : 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AccionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [accion, setAccion] = useState<AccionDetail | null>(null)
  const [historial, setHistorial] = useState<HistorialEstadoEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [transitionError, setTransitionError] = useState('')
  const [transitioning, setTransitioning] = useState(false)

  const accionId = Number(id)
  const canViewHistorial = user?.role === 'admin' || user?.role === 'supervisor'

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [accionData, historialData] = await Promise.all([
          accionesService.getAccion(accionId),
          canViewHistorial ? accionesService.getHistorial(accionId) : Promise.resolve([]),
        ])
        if (!cancelled) {
          setAccion(accionData)
          setHistorial(historialData)
        }
      } catch {
        if (!cancelled) setError('No se pudo cargar la acción.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [accionId, canViewHistorial])

  const nextEstado = accion && user
    ? canTransition(user.role, accion.responsable.id, Number(user.id), accion.estado)
    : null

  async function handleTransitionConfirm(comentario: string) {
    if (!accion || !nextEstado) return
    setTransitioning(true)
    setTransitionError('')
    try {
      const updated = await accionesService.transitionAccion(accion.id, nextEstado, comentario)
      setAccion(updated)
      setShowModal(false)
      if (canViewHistorial) {
        const h = await accionesService.getHistorial(accion.id)
        setHistorial(h)
      }
    } catch (err: unknown) {
      const e = err as { data?: { detail?: string }; message?: string }
      setTransitionError(e?.data?.detail ?? e?.message ?? 'Error al cambiar estado.')
    } finally {
      setTransitioning(false)
    }
  }

  if (loading) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Cargando...</div>
  }

  if (error || !accion) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Acción no encontrada.'}</p>
          <button onClick={() => navigate('/acciones')} className="text-blue-600 hover:underline text-sm">
            Volver a la lista
          </button>
        </div>
      </div>
    )
  }

  const canEdit = user?.role === 'admin' && accion.estado !== 'verificado'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/acciones')}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Volver"
            >
              ←
            </button>
            <h1 className="text-2xl font-bold text-gray-900">Acción #{accion.id}</h1>
            <AccionStatusBadge estado={accion.estado} />
          </div>
          <div className="flex gap-2">
            {nextEstado && (
              <button
                onClick={() => setShowModal(true)}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
              >
                Mover a {ESTADO_LABELS[nextEstado]}
              </button>
            )}
            <Link
              to={`/acciones/${accion.id}/plan`}
              className="rounded-lg border border-blue-300 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
            >
              Plan de Trabajo
            </Link>
            {canEdit && (
              <Link
                to={`/acciones/${accion.id}/edit`}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Editar
              </Link>
            )}
          </div>
        </div>

        {transitionError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {transitionError}
          </div>
        )}

        {/* Detalle */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
            <div>
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Issue vinculado</dt>
              <dd className="mt-1 text-sm text-gray-900">
                <Link to={`/issues/${accion.issue.id}`} className="text-blue-600 hover:underline">
                  {accion.issue.titulo}
                </Link>
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</dt>
              <dd className="mt-1 text-sm text-gray-900">{TIPO_LABELS[accion.tipo] ?? accion.tipo}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Responsable</dt>
              <dd className="mt-1 text-sm text-gray-900">{accion.responsable.nombre_completo}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha límite</dt>
              <dd className="mt-1 text-sm text-gray-900">{accion.fecha_limite}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Resultado esperado</dt>
              <dd className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{accion.resultado_esperado}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Creado</dt>
              <dd className="mt-1 text-sm text-gray-500">{new Date(accion.created_at).toLocaleString('es')}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-gray-500 uppercase tracking-wider">Actualizado</dt>
              <dd className="mt-1 text-sm text-gray-500">{new Date(accion.updated_at).toLocaleString('es')}</dd>
            </div>
          </dl>
        </div>

        {/* Historial */}
        {canViewHistorial && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Historial de estados</h2>
            {historial.length === 0 ? (
              <p className="text-sm text-gray-400">Sin cambios de estado aún.</p>
            ) : (
              <ol className="relative border-l border-gray-200 ml-3 space-y-4">
                {historial.map((h) => (
                  <li key={h.id} className="ml-4">
                    <div className="absolute -left-1.5 mt-1.5 w-3 h-3 rounded-full bg-blue-500" />
                    <p className="text-sm text-gray-800">
                      <span className="font-medium">{ESTADO_LABELS[h.estado_anterior] ?? h.estado_anterior}</span>
                      {' → '}
                      <span className="font-medium">{ESTADO_LABELS[h.estado_nuevo] ?? h.estado_nuevo}</span>
                    </p>
                    {h.comentario && (
                      <p className="text-sm text-gray-500 mt-0.5 italic">&ldquo;{h.comentario}&rdquo;</p>
                    )}
                    <p className="text-xs text-gray-400 mt-0.5">
                      {new Date(h.timestamp).toLocaleString('es')}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </div>

      {showModal && nextEstado && (
        <TransitionModal
          nextEstado={nextEstado}
          onConfirm={handleTransitionConfirm}
          onClose={() => setShowModal(false)}
          loading={transitioning}
        />
      )}
    </div>
  )
}
