import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { accionesService, type AccionListItem, type AccionFilters } from '../../services/acciones'
import { AccionStatusBadge } from '../../components/acciones/AccionStatusBadge'
import { useAuth } from '../../context/AuthContext'

const TIPO_LABELS: Record<string, string> = {
  correctiva: 'Correctiva',
  preventiva: 'Preventiva',
  mejora: 'De Mejora',
}

export default function AccionListPage() {
  const { user } = useAuth()
  const [acciones, setAcciones] = useState<AccionListItem[]>([])
  const [count, setCount] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [filters, setFilters] = useState<AccionFilters>({
    estado: '',
    tipo: '',
    fecha_limite__gte: '',
    fecha_limite__lte: '',
  })

  const load = useCallback(async (currentPage: number, currentFilters: AccionFilters) => {
    setLoading(true)
    setError('')
    try {
      const data = await accionesService.listAcciones({ ...currentFilters, page: currentPage })
      setAcciones(data.results)
      setCount(data.count)
      setHasNext(!!data.next)
      setHasPrev(!!data.previous)
    } catch {
      setError('No se pudieron cargar las acciones.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(page, filters)
  }, [page, filters, load])

  function handleFilterChange(e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) {
    const { name, value } = e.target
    setPage(1)
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  const canCreate = user?.role === 'admin' || user?.role === 'supervisor'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Acciones Correctivas / Preventivas</h1>
          {canCreate && (
            <Link
              to="/acciones/new"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
            >
              Nueva Acción
            </Link>
          )}
        </div>

        {/* Filtros */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label htmlFor="filter-estado" className="block text-xs font-medium text-gray-600 mb-1">
                Estado
              </label>
              <select
                id="filter-estado"
                name="estado"
                value={filters.estado}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="abierto">Abierto</option>
                <option value="en_proceso">En Proceso</option>
                <option value="cerrado">Cerrado</option>
                <option value="verificado">Verificado</option>
              </select>
            </div>

            <div>
              <label htmlFor="filter-tipo" className="block text-xs font-medium text-gray-600 mb-1">
                Tipo
              </label>
              <select
                id="filter-tipo"
                name="tipo"
                value={filters.tipo}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="correctiva">Correctiva</option>
                <option value="preventiva">Preventiva</option>
                <option value="mejora">De Mejora</option>
              </select>
            </div>

            <div>
              <label htmlFor="filter-fecha-desde" className="block text-xs font-medium text-gray-600 mb-1">
                Fecha límite desde
              </label>
              <input
                id="filter-fecha-desde"
                type="date"
                name="fecha_limite__gte"
                value={filters.fecha_limite__gte}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="filter-fecha-hasta" className="block text-xs font-medium text-gray-600 mb-1">
                Fecha límite hasta
              </label>
              <input
                id="filter-fecha-hasta"
                type="date"
                name="fecha_limite__lte"
                value={filters.fecha_limite__lte}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-gray-500">Cargando...</div>
          ) : acciones.length === 0 ? (
            <div className="p-12 text-center text-gray-400">No se encontraron acciones.</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Issue
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Resultado esperado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Responsable
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Fecha límite
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {acciones.map((accion) => (
                  <tr key={accion.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-600">
                      <Link to={`/issues/${accion.issue.id}`} className="text-blue-600 hover:underline">
                        {accion.issue.titulo}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {TIPO_LABELS[accion.tipo] ?? accion.tipo}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700 max-w-xs truncate">
                      {accion.resultado_esperado_resumen}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {accion.responsable.nombre_completo}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{accion.fecha_limite}</td>
                    <td className="px-4 py-3">
                      <AccionStatusBadge estado={accion.estado} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/acciones/${accion.id}`}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                      >
                        Ver
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {(hasPrev || hasNext) && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-gray-500">{count} resultados</span>
            <div className="flex gap-2">
              {hasPrev && (
                <button
                  onClick={() => setPage((p) => p - 1)}
                  className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                >
                  Anterior
                </button>
              )}
              {hasNext && (
                <button
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
                >
                  Siguiente
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
