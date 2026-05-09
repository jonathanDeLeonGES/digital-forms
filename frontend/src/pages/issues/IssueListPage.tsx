import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { issuesService, type IssueListItem, type IssueFilters } from '../../services/issues'
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

export default function IssueListPage() {
  const [issues, setIssues] = useState<IssueListItem[]>([])
  const [count, setCount] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [filters, setFilters] = useState<IssueFilters>({
    tipo: '',
    estado: '',
    gravedad: '',
    area: '',
    fecha_evento__gte: '',
    fecha_evento__lte: '',
  })

  const load = useCallback(
    async (currentPage: number, currentFilters: IssueFilters) => {
      setLoading(true)
      setError('')
      try {
        const data = await issuesService.getIssues({ ...currentFilters, page: currentPage })
        setIssues(data.results)
        setCount(data.count)
        setHasNext(!!data.next)
        setHasPrev(!!data.previous)
      } catch {
        setError('No se pudieron cargar los issues.')
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    load(page, filters)
  }, [page, filters, load])

  function handleFilterChange(e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) {
    const { name, value } = e.target
    setPage(1)
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Issues de Seguridad</h1>
          <Link
            to="/issues/new"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            Nuevo Issue
          </Link>
        </div>

        {/* Filtros */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <div>
              <label htmlFor="filter-tipo" className="block text-xs font-medium text-gray-600 mb-1">
                Tipo
              </label>
              <select
                id="filter-tipo"
                name="tipo"
                aria-label="Tipo"
                value={filters.tipo}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="incidente">Incidente</option>
                <option value="casi_incidente">Casi Incidente</option>
                <option value="reunion_seguridad">Reunión de Seguridad</option>
              </select>
            </div>

            <div>
              <label htmlFor="filter-estado" className="block text-xs font-medium text-gray-600 mb-1">
                Estado
              </label>
              <select
                id="filter-estado"
                name="estado"
                aria-label="Estado"
                value={filters.estado}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="abierto">Abierto</option>
                <option value="en_analisis">En Análisis</option>
                <option value="acciones_generadas">Acciones Generadas</option>
                <option value="cerrado">Cerrado</option>
              </select>
            </div>

            <div>
              <label htmlFor="filter-gravedad" className="block text-xs font-medium text-gray-600 mb-1">
                Gravedad
              </label>
              <select
                id="filter-gravedad"
                name="gravedad"
                aria-label="Gravedad"
                value={filters.gravedad}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todas</option>
                <option value="baja">Baja</option>
                <option value="media">Media</option>
                <option value="alta">Alta</option>
                <option value="critica">Crítica</option>
              </select>
            </div>

            <div>
              <label htmlFor="filter-fecha-desde" className="block text-xs font-medium text-gray-600 mb-1">
                Desde
              </label>
              <input
                id="filter-fecha-desde"
                type="date"
                name="fecha_evento__gte"
                value={filters.fecha_evento__gte}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label htmlFor="filter-fecha-hasta" className="block text-xs font-medium text-gray-600 mb-1">
                Hasta
              </label>
              <input
                id="filter-fecha-hasta"
                type="date"
                name="fecha_evento__lte"
                value={filters.fecha_evento__lte}
                onChange={handleFilterChange}
                className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Tabla */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-gray-500">Cargando...</div>
          ) : issues.length === 0 ? (
            <div className="p-12 text-center text-gray-400">No se encontraron issues.</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Título
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Área
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Gravedad
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {issues.map((issue) => (
                  <tr key={issue.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {TIPO_LABELS[issue.tipo] ?? issue.tipo}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {issue.titulo}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{issue.area}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {GRAVEDAD_LABELS[issue.gravedad] ?? issue.gravedad}
                    </td>
                    <td className="px-4 py-3">
                      <IssueStatusBadge estado={issue.estado} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{issue.fecha_evento}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/issues/${issue.id}`}
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

        {/* Paginación */}
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
