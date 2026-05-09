import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { issuesService, type IssueDetail, type CausaRaiz } from '../../services/issues'
import { IssueStatusBadge } from '../../components/issues/IssueStatusBadge'

const TIPO_LABELS: Record<string, string> = {
  incidente: 'Incidente',
  casi_incidente: 'Casi Incidente',
  reunion_seguridad: 'Reunión de Seguridad',
}

const GRAVEDAD_LABELS: Record<string, string> = {
  baja: 'Baja',
  media: 'Media',
  alta: 'Alta',
  critica: 'Crítica',
}

const TRANSICIONES_VALIDAS: Record<string, string[]> = {
  abierto: ['en_analisis'],
  en_analisis: ['acciones_generadas', 'abierto'],
  acciones_generadas: ['cerrado'],
  cerrado: [],
}

const ESTADO_LABELS: Record<string, string> = {
  abierto: 'Abierto',
  en_analisis: 'En Análisis',
  acciones_generadas: 'Acciones Generadas',
  cerrado: 'Cerrado',
}

const ADMIN_ROLES = new Set(['admin', 'supervisor'])

function getUserRole(): string {
  try {
    const user = JSON.parse(localStorage.getItem('user') ?? '{}')
    return user.role ?? 'responsable'
  } catch {
    return 'responsable'
  }
}

function getReportadoPorName(issue: IssueDetail): string {
  if (typeof issue.reportado_por === 'object' && issue.reportado_por !== null) {
    return issue.reportado_por.nombre_completo
  }
  return String(issue.reportado_por)
}

interface IshikawaSectionProps {
  categorias: Record<string, CausaRaiz[]>
}

function IshikawaSection({ categorias }: IshikawaSectionProps) {
  const entries = Object.entries(categorias).filter(([, causas]) => causas.length > 0)
  if (entries.length === 0) {
    return <p className="text-sm text-gray-400">No hay causas registradas en este Ishikawa.</p>
  }

  return (
    <div className="space-y-4">
      {entries.map(([cat, causas]) => (
        <div key={cat}>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            {cat}
          </h4>
          <ul className="space-y-2">
            {causas.map((causa) => (
              <li key={causa.id} className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-800">{causa.descripcion}</p>
                {causa.subcausas.length > 0 && (
                  <ul className="mt-1 ml-4 space-y-1">
                    {causa.subcausas.map((sub) => (
                      <li key={sub.id} className="text-xs text-gray-600 flex items-start gap-1">
                        <span className="text-gray-400">↳</span> {sub.descripcion}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

export default function IssueDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [issue, setIssue] = useState<IssueDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [transitioning, setTransitioning] = useState(false)

  const userRole = getUserRole()
  const isAdminOrSupervisor = ADMIN_ROLES.has(userRole)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    issuesService
      .getIssue(Number(id))
      .then(setIssue)
      .catch(() => setError('No se pudo cargar el issue.'))
      .finally(() => setLoading(false))
  }, [id])

  async function handleTransition(nuevoEstado: string) {
    if (!issue) return
    setTransitioning(true)
    try {
      const updated = await issuesService.transitionIssue(issue.id, nuevoEstado, '')
      setIssue(updated)
    } catch {
      setError('No se pudo realizar la transición de estado.')
    } finally {
      setTransitioning(false)
    }
  }

  if (loading) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center">Cargando...</div>
  }

  if (error || !issue) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-red-600">{error || 'Issue no encontrado.'}</p>
      </div>
    )
  }

  const transicionesDisponibles = isAdminOrSupervisor
    ? TRANSICIONES_VALIDAS[issue.estado] ?? []
    : []

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <IssueStatusBadge estado={issue.estado} />
              <span className="text-xs text-gray-400">
                {TIPO_LABELS[issue.tipo] ?? issue.tipo}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">{issue.titulo}</h1>
          </div>
          <Link
            to={`/issues/${issue.id}/edit`}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Editar
          </Link>
        </div>

        {/* Transition buttons */}
        {transicionesDisponibles.length > 0 && (
          <div className="flex items-center gap-2 mb-6">
            <span className="text-sm text-gray-500">Transicionar a:</span>
            {transicionesDisponibles.map((estado) => (
              <button
                key={estado}
                type="button"
                onClick={() => handleTransition(estado)}
                disabled={transitioning}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-60"
              >
                {ESTADO_LABELS[estado] ?? estado}
              </button>
            ))}
          </div>
        )}

        {/* Main info */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Área</p>
              <p className="text-sm text-gray-900 mt-0.5">{issue.area}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Gravedad</p>
              <p className="text-sm text-gray-900 mt-0.5">{GRAVEDAD_LABELS[issue.gravedad] ?? issue.gravedad}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Fecha del evento</p>
              <p className="text-sm text-gray-900 mt-0.5">{issue.fecha_evento}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Reportado por</p>
              <p className="text-sm text-gray-900 mt-0.5">{getReportadoPorName(issue)}</p>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Descripción</p>
            <p className="text-sm text-gray-800 leading-relaxed">{issue.descripcion}</p>
          </div>
        </div>

        {/* Ishikawa */}
        {issue.ishikawa && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Diagrama de Ishikawa
            </h2>
            <IshikawaSection categorias={issue.ishikawa.categorias} />
          </div>
        )}

        {/* Historial — solo admin/supervisor */}
        {isAdminOrSupervisor && issue.historial_estados.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Historial de estados
            </h2>
            <ul className="space-y-2">
              {issue.historial_estados.map((entry) => (
                <li key={entry.id} className="flex items-center gap-3 text-sm text-gray-600">
                  <span className="text-xs text-gray-400">
                    {new Date(entry.timestamp).toLocaleString('es-GT')}
                  </span>
                  <span>
                    {entry.estado_anterior} → {entry.estado_nuevo}
                  </span>
                  {entry.comentario && (
                    <span className="text-gray-400 italic">"{entry.comentario}"</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4">
          <Link to="/issues" className="text-sm text-blue-600 hover:underline">
            ← Volver al listado
          </Link>
        </div>
      </div>
    </div>
  )
}
