import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { issuesService, type IssueWriteData } from '../../services/issues'
import IshikawaForm, { type IshikawaValue } from '../../components/issues/IshikawaForm'

interface FormState {
  tipo: string
  titulo: string
  descripcion: string
  fecha_evento: string
  area: string
  gravedad: string
}

interface FormErrors {
  tipo?: string
  titulo?: string
  descripcion?: string
  fecha_evento?: string
  area?: string
  gravedad?: string
  non_field?: string
}

function validateForm(form: FormState): FormErrors {
  const errors: FormErrors = {}
  if (!form.titulo.trim()) errors.titulo = 'El título es requerido.'
  if (!form.descripcion.trim()) errors.descripcion = 'La descripción es requerida.'
  if (!form.area.trim()) errors.area = 'El área es requerida.'
  if (!form.tipo) errors.tipo = 'El tipo es requerido.'
  if (!form.gravedad) errors.gravedad = 'La gravedad es requerida.'
  if (!form.fecha_evento) errors.fecha_evento = 'La fecha del evento es requerida.'
  return errors
}

function hasErrors(errors: FormErrors): boolean {
  return Object.values(errors).some(Boolean)
}

export default function IssueFormPage() {
  const { id } = useParams<{ id?: string }>()
  const isEdit = !!id
  const navigate = useNavigate()

  const [form, setForm] = useState<FormState>({
    tipo: '',
    titulo: '',
    descripcion: '',
    fecha_evento: '',
    area: '',
    gravedad: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [ishikawa, setIshikawa] = useState<IshikawaValue>({})
  const [loading, setLoading] = useState(false)
  const [loadingIssue, setLoadingIssue] = useState(isEdit)

  useEffect(() => {
    if (!isEdit || !id) return
    setLoadingIssue(true)
    issuesService.getIssue(Number(id)).then((issue) => {
      setForm({
        tipo: issue.tipo,
        titulo: issue.titulo,
        descripcion: issue.descripcion,
        fecha_evento: issue.fecha_evento,
        area: issue.area,
        gravedad: issue.gravedad,
      })
      if (issue.ishikawa?.categorias) {
        const val: IshikawaValue = {}
        for (const [cat, causas] of Object.entries(issue.ishikawa.categorias)) {
          if (causas.length > 0) val[cat] = causas
        }
        setIshikawa(val)
      }
      setLoadingIssue(false)
    }).catch(() => setLoadingIssue(false))
  }, [id, isEdit])

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const clientErrors = validateForm(form)
    if (hasErrors(clientErrors)) {
      setErrors(clientErrors)
      return
    }
    setErrors({})
    setLoading(true)

    try {
      const data: IssueWriteData = { ...form }
      let issue
      if (isEdit) {
        issue = await issuesService.updateIssue(Number(id), data)
      } else {
        issue = await issuesService.createIssue(data)
      }

      // Save Ishikawa if any causas were entered
      const causas = Object.entries(ishikawa).flatMap(([categoria, causaList]) =>
        causaList.map((c) => ({ categoria, descripcion: c.descripcion, subcausas: c.subcausas })),
      )
      if (causas.length > 0) {
        await issuesService.updateIshikawa(issue.id, { causas })
      }

      navigate(`/issues/${issue.id}`)
    } catch (err: unknown) {
      const apiErr = err as { data?: Record<string, string[]> }
      if (apiErr?.data) {
        const apiErrors: FormErrors = {}
        for (const [k, v] of Object.entries(apiErr.data)) {
          if (k === 'non_field_errors') {
            apiErrors.non_field = Array.isArray(v) ? v[0] : String(v)
          } else {
            ;(apiErrors as Record<string, string>)[k] = Array.isArray(v) ? v[0] : String(v)
          }
        }
        setErrors(apiErrors)
      } else {
        setErrors({ non_field: 'Ocurrió un error inesperado.' })
      }
    } finally {
      setLoading(false)
    }
  }

  if (loadingIssue) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center">Cargando...</div>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            {isEdit ? 'Editar Issue' : 'Nuevo Issue'}
          </h1>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-6">
          {/* Issue fields */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              Datos del evento
            </h2>

            {errors.non_field && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                {errors.non_field}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="tipo" className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo
                </label>
                <select
                  id="tipo"
                  name="tipo"
                  value={form.tipo}
                  onChange={handleChange}
                  className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.tipo ? 'border-red-400' : 'border-gray-300'
                  }`}
                >
                  <option value="">Seleccione tipo</option>
                  <option value="incidente">Incidente</option>
                  <option value="casi_incidente">Casi Incidente</option>
                  <option value="reunion_seguridad">Reunión de Seguridad</option>
                </select>
                {errors.tipo && <p className="mt-1 text-xs text-red-600">{errors.tipo}</p>}
              </div>

              <div>
                <label htmlFor="gravedad" className="block text-sm font-medium text-gray-700 mb-1">
                  Gravedad
                </label>
                <select
                  id="gravedad"
                  name="gravedad"
                  value={form.gravedad}
                  onChange={handleChange}
                  className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.gravedad ? 'border-red-400' : 'border-gray-300'
                  }`}
                >
                  <option value="">Seleccione gravedad</option>
                  <option value="baja">Baja</option>
                  <option value="media">Media</option>
                  <option value="alta">Alta</option>
                  <option value="critica">Crítica</option>
                </select>
                {errors.gravedad && <p className="mt-1 text-xs text-red-600">{errors.gravedad}</p>}
              </div>
            </div>

            <div>
              <label htmlFor="titulo" className="block text-sm font-medium text-gray-700 mb-1">
                Título
              </label>
              <input
                id="titulo"
                name="titulo"
                type="text"
                value={form.titulo}
                onChange={handleChange}
                placeholder="Breve descripción del evento"
                className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.titulo ? 'border-red-400' : 'border-gray-300'
                }`}
              />
              {errors.titulo && <p className="mt-1 text-xs text-red-600">{errors.titulo}</p>}
            </div>

            <div>
              <label htmlFor="descripcion" className="block text-sm font-medium text-gray-700 mb-1">
                Descripción
              </label>
              <textarea
                id="descripcion"
                name="descripcion"
                rows={4}
                value={form.descripcion}
                onChange={handleChange}
                placeholder="Descripción detallada del evento"
                className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.descripcion ? 'border-red-400' : 'border-gray-300'
                }`}
              />
              {errors.descripcion && (
                <p className="mt-1 text-xs text-red-600">{errors.descripcion}</p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="area" className="block text-sm font-medium text-gray-700 mb-1">
                  Área
                </label>
                <input
                  id="area"
                  name="area"
                  type="text"
                  value={form.area}
                  onChange={handleChange}
                  placeholder="Ej: Producción, Bodega..."
                  className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.area ? 'border-red-400' : 'border-gray-300'
                  }`}
                />
                {errors.area && <p className="mt-1 text-xs text-red-600">{errors.area}</p>}
              </div>

              <div>
                <label htmlFor="fecha_evento" className="block text-sm font-medium text-gray-700 mb-1">
                  Fecha del evento
                </label>
                <input
                  id="fecha_evento"
                  name="fecha_evento"
                  type="date"
                  value={form.fecha_evento}
                  onChange={handleChange}
                  className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.fecha_evento ? 'border-red-400' : 'border-gray-300'
                  }`}
                />
                {errors.fecha_evento && (
                  <p className="mt-1 text-xs text-red-600">{errors.fecha_evento}</p>
                )}
              </div>
            </div>
          </div>

          {/* Ishikawa section */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Diagrama de Ishikawa (opcional)
            </h2>
            <IshikawaForm value={ishikawa} onChange={setIshikawa} />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
