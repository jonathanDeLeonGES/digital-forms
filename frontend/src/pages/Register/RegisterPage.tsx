import { useState, type ChangeEvent, type FormEvent } from 'react'

interface FormState {
  nombre_empresa: string
  subdominio: string
  email_admin: string
}

interface FormErrors {
  nombre_empresa?: string[]
  subdominio?: string[]
  email_admin?: string[]
  non_field?: string[]
}

interface SuccessState {
  subdominio: string
  trial_expires_at: string
}

const SUBDOMAIN_RE = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validateForm(form: FormState): FormErrors {
  const errors: FormErrors = {}

  if (!form.nombre_empresa.trim()) {
    errors.nombre_empresa = ['El nombre de empresa es requerido.']
  }

  if (!form.subdominio) {
    errors.subdominio = ['El subdominio es requerido.']
  } else if (!SUBDOMAIN_RE.test(form.subdominio)) {
    errors.subdominio = [
      'El subdominio solo puede contener letras minúsculas, dígitos y guiones, y debe comenzar y terminar con una letra o dígito.',
    ]
  }

  if (!form.email_admin.trim()) {
    errors.email_admin = ['El email es requerido.']
  } else if (!EMAIL_RE.test(form.email_admin)) {
    errors.email_admin = ['Ingrese un email válido.']
  }

  return errors
}

function hasErrors(errors: FormErrors): boolean {
  return Object.values(errors).some((v) => v && v.length > 0)
}

function FieldErrors({ messages }: { messages?: string[] }) {
  if (!messages || messages.length === 0) return null
  return (
    <ul className="mt-1 space-y-0.5">
      {messages.map((msg, i) => (
        <li key={i} className="text-sm text-red-600">
          {msg}
        </li>
      ))}
    </ul>
  )
}

export default function RegisterPage() {
  const [form, setForm] = useState<FormState>({
    nombre_empresa: '',
    subdominio: '',
    email_admin: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState<SuccessState | null>(null)

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target
    if (name === 'subdominio') {
      // Normalize: lowercase, strip invalid chars
      const normalized = value.toLowerCase().replace(/[^a-z0-9-]/g, '')
      setForm((prev) => ({ ...prev, subdominio: normalized }))
    } else {
      setForm((prev) => ({ ...prev, [name]: value }))
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()

    const clientErrors = validateForm(form)
    if (hasErrors(clientErrors)) {
      setErrors(clientErrors)
      return
    }

    setLoading(true)
    setErrors({})

    try {
      const response = await fetch('/api/public/tenants/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })

      if (response.status === 201) {
        const data = await response.json()
        setSuccess({ subdominio: data.subdominio, trial_expires_at: data.trial_expires_at })
      } else if (response.status === 400) {
        const data = await response.json()
        setErrors(data as FormErrors)
      } else if (response.status === 409) {
        const data = await response.json()
        setErrors({ non_field: [data.detail] })
      } else {
        setErrors({ non_field: ['Ocurrió un error inesperado. Intente de nuevo.'] })
      }
    } catch {
      setErrors({ non_field: ['No se pudo conectar con el servidor. Verifique su conexión.'] })
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    const expiresDate = new Date(success.trial_expires_at).toLocaleDateString('es-GT', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <div className="flex justify-center mb-4">
            <span className="text-5xl">✅</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">¡Registro exitoso!</h1>
          <p className="text-gray-600 mb-6">
            Su empresa ya tiene acceso al SGCA. Su período de prueba vence el{' '}
            <strong>{expiresDate}</strong>.
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-700 font-medium mb-1">URL de acceso de su empresa:</p>
            <p className="text-lg font-bold text-blue-900">{success.subdominio}.sgca.com</p>
          </div>
          <p className="text-sm text-gray-500">
            Comparta esta URL con los usuarios de su empresa para que puedan acceder al sistema.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Registrar empresa</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Cree su espacio de trabajo en el SGCA con 14 días de prueba gratuita.
          </p>
        </div>

        {errors.non_field && errors.non_field.length > 0 && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-3">
            {errors.non_field.map((msg, i) => (
              <p key={i} className="text-sm text-red-700">
                {msg}
              </p>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          <div>
            <label htmlFor="nombre_empresa" className="block text-sm font-medium text-gray-700 mb-1">
              Nombre de empresa
            </label>
            <input
              id="nombre_empresa"
              name="nombre_empresa"
              type="text"
              autoComplete="organization"
              value={form.nombre_empresa}
              onChange={handleChange}
              placeholder="Ej: Industrias Guatemala S.A."
              className={`w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.nombre_empresa ? 'border-red-400' : 'border-gray-300'
              }`}
            />
            <FieldErrors messages={errors.nombre_empresa} />
          </div>

          <div>
            <label htmlFor="subdominio" className="block text-sm font-medium text-gray-700 mb-1">
              Subdominio
            </label>
            <div className="flex items-center rounded-lg border shadow-sm focus-within:ring-2 focus-within:ring-blue-500 overflow-hidden ${errors.subdominio ? 'border-red-400' : 'border-gray-300'}">
              <input
                id="subdominio"
                name="subdominio"
                type="text"
                autoComplete="off"
                value={form.subdominio}
                onChange={handleChange}
                placeholder="miempresa"
                className={`flex-1 px-3 py-2 text-sm focus:outline-none border-0 ${
                  errors.subdominio ? 'bg-red-50' : ''
                }`}
              />
              <span className="px-3 py-2 bg-gray-100 text-gray-500 text-sm border-l border-gray-300 select-none">
                .sgca.com
              </span>
            </div>
            <p className="mt-1 text-xs text-gray-400">
              Solo letras minúsculas, dígitos y guiones. Ej: mi-empresa
            </p>
            <FieldErrors messages={errors.subdominio} />
          </div>

          <div>
            <label htmlFor="email_admin" className="block text-sm font-medium text-gray-700 mb-1">
              Email del administrador
            </label>
            <input
              id="email_admin"
              name="email_admin"
              type="email"
              autoComplete="email"
              value={form.email_admin}
              onChange={handleChange}
              placeholder="admin@miempresa.com"
              className={`w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.email_admin ? 'border-red-400' : 'border-gray-300'
              }`}
            />
            <FieldErrors messages={errors.email_admin} />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Registrando...' : 'Crear cuenta de prueba'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-gray-400">
          ¿Ya tiene una cuenta?{' '}
          <a href="#" className="text-blue-600 hover:underline">
            Inicie sesión desde su subdominio.
          </a>
        </p>
      </div>
    </div>
  )
}
