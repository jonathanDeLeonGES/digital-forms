import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchWithAuth } from '../../services/fetchWithAuth'

interface FormState {
  nombre_completo: string
  email: string
  role: string
  password: string
}

const ROLES = [
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'responsable', label: 'Responsable' },
  { value: 'verificador', label: 'Verificador' },
  { value: 'admin', label: 'Administrador' },
]

export default function UserFormPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [form, setForm] = useState<FormState>({
    nombre_completo: '',
    email: '',
    role: 'responsable',
    password: '',
  })
  const [loading, setLoading] = useState(isEdit)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!isEdit) return
    async function load() {
      setLoading(true)
      try {
        const resp = await fetchWithAuth(`/api/users/${id}/`)
        if (!resp.ok) throw new Error()
        const data = await resp.json()
        setForm({ nombre_completo: data.nombre_completo, email: data.email, role: data.role, password: '' })
      } catch {
        setError('No se pudo cargar el usuario.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, isEdit])

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
    setFieldErrors((prev) => ({ ...prev, [name]: '' }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    setFieldErrors({})

    try {
      let resp: Response
      if (isEdit) {
        const body: Record<string, string> = {
          nombre_completo: form.nombre_completo,
          email: form.email,
          role: form.role,
        }
        resp = await fetchWithAuth(`/api/users/${id}/`, { method: 'PUT', body: JSON.stringify(body) })
      } else {
        resp = await fetchWithAuth('/api/users/', { method: 'POST', body: JSON.stringify(form) })
      }

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        if (body.detail) {
          setError(body.detail)
        } else {
          const fields: Record<string, string> = {}
          for (const [k, v] of Object.entries(body)) {
            fields[k] = Array.isArray(v) ? v.join(' ') : String(v)
          }
          setFieldErrors(fields)
        }
        return
      }

      navigate('/admin/usuarios')
    } catch {
      setError('Ocurrió un error inesperado.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center text-gray-500">Cargando...</div>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-lg mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => navigate('/admin/usuarios')} className="text-gray-400 hover:text-gray-600" aria-label="Volver">
            ←
          </button>
          <h1 className="text-2xl font-bold text-gray-900">
            {isEdit ? 'Editar usuario' : 'Nuevo usuario'}
          </h1>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-5">
          <div>
            <label htmlFor="nombre_completo" className="block text-sm font-medium text-gray-700 mb-1">
              Nombre completo <span className="text-red-500">*</span>
            </label>
            <input
              id="nombre_completo"
              name="nombre_completo"
              type="text"
              value={form.nombre_completo}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {fieldErrors.nombre_completo && <p className="mt-1 text-xs text-red-600">{fieldErrors.nombre_completo}</p>}
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              id="email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
          </div>

          <div>
            <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1">
              Rol <span className="text-red-500">*</span>
            </label>
            <select
              id="role"
              name="role"
              value={form.role}
              onChange={handleChange}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
            {fieldErrors.role && <p className="mt-1 text-xs text-red-600">{fieldErrors.role}</p>}
          </div>

          {!isEdit && (
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña <span className="text-red-500">*</span>
              </label>
              <input
                id="password"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                required
                minLength={8}
                placeholder="Mínimo 8 caracteres"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {fieldErrors.password && <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/admin/usuarios')}
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
              {submitting ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
