import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { accionesService, type AccionWriteData } from '../../services/acciones'
import type { IssueListItem } from '../../services/issues'
import { issuesService } from '../../services/issues'
import { fetchWithAuth } from '../../services/fetchWithAuth'

interface UserOption {
  id: number
  nombre_completo: string
  email: string
  role: string
}

async function fetchUsers(): Promise<UserOption[]> {
  const resp = await fetchWithAuth('/api/users/')
  if (!resp.ok) return []
  const data = await resp.json()
  return Array.isArray(data) ? data : (data.results ?? [])
}

export default function AccionFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [issues, setIssues] = useState<IssueListItem[]>([])
  const [users, setUsers] = useState<UserOption[]>([])
  const [loading, setLoading] = useState(isEdit)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const [form, setForm] = useState<AccionWriteData>({
    issue_id: 0,
    tipo: 'correctiva',
    resultado_esperado: '',
    responsable_id: 0,
    fecha_limite: '',
  })
  const [isVerified, setIsVerified] = useState(false)

  useEffect(() => {
    async function loadOptions() {
      const [issueData, userData] = await Promise.all([
        issuesService.getIssues({ estado: 'en_analisis', page_size: 100 } as never)
          .then(async (r) => {
            const r2 = await issuesService.getIssues({ estado: 'acciones_generadas', page_size: 100 } as never).catch(() => ({ results: [] as IssueListItem[] }))
            return { results: [...r.results, ...r2.results] }
          })
          .catch(() => ({ results: [] as IssueListItem[] })),
        fetchUsers(),
      ])
      setIssues(issueData.results)
      setUsers(userData)
    }
    loadOptions()
  }, [])

  useEffect(() => {
    if (!isEdit) return
    async function loadAccion() {
      setLoading(true)
      try {
        const accion = await accionesService.getAccion(Number(id))
        setIsVerified(accion.estado === 'verificado')
        setForm({
          issue_id: accion.issue.id,
          tipo: accion.tipo,
          resultado_esperado: accion.resultado_esperado,
          responsable_id: accion.responsable.id,
          fecha_limite: accion.fecha_limite,
        })
      } catch {
        setError('No se pudo cargar la acción.')
      } finally {
        setLoading(false)
      }
    }
    loadAccion()
  }, [id, isEdit])

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: name.endsWith('_id') ? Number(value) : value }))
    setFieldErrors((prev) => ({ ...prev, [name]: '' }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    setFieldErrors({})
    try {
      if (isEdit) {
        await accionesService.updateAccion(Number(id), form)
        navigate(`/acciones/${id}`)
      } else {
        const created = await accionesService.createAccion(form)
        navigate(`/acciones/${created.id}`)
      }
    } catch (err: unknown) {
      const e = err as { data?: Record<string, string | string[]>; message?: string }
      if (e?.data && typeof e.data === 'object') {
        const detail = e.data.detail
        if (typeof detail === 'string') {
          setError(detail)
        } else {
          const fields: Record<string, string> = {}
          for (const [k, v] of Object.entries(e.data)) {
            fields[k] = Array.isArray(v) ? v.join(' ') : String(v)
          }
          setFieldErrors(fields)
        }
      } else {
        setError(e?.message ?? 'Ocurrió un error inesperado.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const disabled = isVerified || submitting

  if (loading) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Cargando...</div>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate(isEdit ? `/acciones/${id}` : '/acciones')}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Volver"
          >
            ←
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEdit ? 'Editar acción' : 'Nueva acción'}
          </h1>
        </div>

        {isVerified && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4 text-sm text-yellow-800">
            Esta acción está verificada y no puede editarse.
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
          {/* Issue */}
          <div>
            <label htmlFor="issue_id" className="block text-sm font-medium text-gray-700 mb-1">
              Issue vinculado <span className="text-red-500">*</span>
            </label>
            <select
              id="issue_id"
              name="issue_id"
              value={form.issue_id || ''}
              onChange={handleChange}
              disabled={disabled}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            >
              <option value="">Seleccionar issue...</option>
              {issues.map((issue) => (
                <option key={issue.id} value={issue.id}>
                  #{issue.id} — {issue.titulo}
                </option>
              ))}
            </select>
            {fieldErrors.issue_id && <p className="mt-1 text-xs text-red-600">{fieldErrors.issue_id}</p>}
          </div>

          {/* Tipo */}
          <div>
            <label htmlFor="tipo" className="block text-sm font-medium text-gray-700 mb-1">
              Tipo <span className="text-red-500">*</span>
            </label>
            <select
              id="tipo"
              name="tipo"
              value={form.tipo}
              onChange={handleChange}
              disabled={disabled}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            >
              <option value="correctiva">Correctiva</option>
              <option value="preventiva">Preventiva</option>
              <option value="mejora">De Mejora</option>
            </select>
            {fieldErrors.tipo && <p className="mt-1 text-xs text-red-600">{fieldErrors.tipo}</p>}
          </div>

          {/* Resultado esperado */}
          <div>
            <label htmlFor="resultado_esperado" className="block text-sm font-medium text-gray-700 mb-1">
              Resultado esperado <span className="text-red-500">*</span>
            </label>
            <textarea
              id="resultado_esperado"
              name="resultado_esperado"
              value={form.resultado_esperado}
              onChange={handleChange}
              disabled={disabled}
              required
              rows={4}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            />
            {fieldErrors.resultado_esperado && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.resultado_esperado}</p>
            )}
          </div>

          {/* Responsable */}
          <div>
            <label htmlFor="responsable_id" className="block text-sm font-medium text-gray-700 mb-1">
              Responsable <span className="text-red-500">*</span>
            </label>
            <select
              id="responsable_id"
              name="responsable_id"
              value={form.responsable_id || ''}
              onChange={handleChange}
              disabled={disabled}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            >
              <option value="">Seleccionar responsable...</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nombre_completo} ({u.role})
                </option>
              ))}
            </select>
            {fieldErrors.responsable_id && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.responsable_id}</p>
            )}
          </div>

          {/* Fecha límite */}
          <div>
            <label htmlFor="fecha_limite" className="block text-sm font-medium text-gray-700 mb-1">
              Fecha límite <span className="text-red-500">*</span>
            </label>
            <input
              id="fecha_limite"
              type="date"
              name="fecha_limite"
              value={form.fecha_limite}
              onChange={handleChange}
              disabled={disabled}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
            />
            {fieldErrors.fecha_limite && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.fecha_limite}</p>
            )}
          </div>

          {!isVerified && (
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => navigate(isEdit ? `/acciones/${id}` : '/acciones')}
                disabled={submitting}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear acción'}
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
