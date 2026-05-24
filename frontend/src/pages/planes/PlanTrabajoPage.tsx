import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { planesService, type PlanDetalle } from '../../services/planes'
import { ProgressBar } from '../../components/planes/ProgressBar'
import { ActividadCard } from '../../components/planes/ActividadCard'

export default function PlanTrabajoPage() {
  const { accionId } = useParams<{ accionId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [plan, setPlan] = useState<PlanDetalle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const canManage = user?.role === 'admin' || user?.role === 'supervisor'

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await planesService.getPlanByAccion(Number(accionId))
      setPlan(data)
    } catch {
      setError('No se pudo cargar el plan de trabajo.')
    } finally {
      setLoading(false)
    }
  }, [accionId])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px] text-gray-400 text-sm">
        Cargando plan...
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 text-sm mb-4">{error}</p>
        <button onClick={() => navigate(-1)} className="text-blue-600 hover:underline text-sm">Volver</button>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 text-sm mb-4">Esta acción no tiene un plan de trabajo todavía.</p>
        <button onClick={() => navigate(-1)} className="text-blue-600 hover:underline text-sm">Volver</button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate(`/acciones/${accionId}`)}
          className="text-gray-400 hover:text-gray-600 text-lg"
          aria-label="Volver a la acción"
        >
          ←
        </button>
        <h1 className="text-xl font-bold text-gray-900">Plan de Trabajo — Acción #{accionId}</h1>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-700">Progreso general</span>
          <span className="text-xs text-gray-500">
            {plan.actividades.filter((a) => a.estado === 'completada').length} / {plan.actividades.length} actividades
          </span>
        </div>
        <ProgressBar progreso={plan.progreso} />
      </div>

      <div className="space-y-3">
        {plan.actividades.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">Sin actividades en este plan.</p>
        ) : (
          plan.actividades.map((actividad) => (
            <ActividadCard
              key={actividad.id}
              actividad={actividad}
              userRole={user?.role ?? ''}
              userId={Number(user?.id ?? 0)}
              canManage={canManage}
              onChanged={load}
            />
          ))
        )}
      </div>
    </div>
  )
}
