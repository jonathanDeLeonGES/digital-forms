import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

function buildTenantUrl(subdomain: string): string {
  const { protocol, hostname, port } = window.location
  const portSuffix = port ? `:${port}` : ''
  return `${protocol}//${subdomain}.${hostname}${portSuffix}/login`
}

export default function LandingPage() {
  const [subdomain, setSubdomain] = useState('')
  const [error, setError] = useState('')

  function handleAccess(e: FormEvent) {
    e.preventDefault()
    const cleaned = subdomain.trim().toLowerCase()
    if (!cleaned) {
      setError('Ingresa el subdominio de tu empresa.')
      return
    }
    setError('')
    window.location.assign(buildTenantUrl(cleaned))
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-extrabold text-blue-700 mb-3">SGCA</h1>
          <p className="text-xl text-gray-600 max-w-md mx-auto">
            Sistema de Gestión de Correcciones y Acciones
          </p>
          <p className="text-gray-400 mt-2 text-sm max-w-sm mx-auto">
            Registra incidentes, analiza causas raíz y gestiona acciones correctivas con tu equipo.
          </p>
        </div>

        <div className="w-full max-w-xl grid md:grid-cols-2 gap-6">
          {/* Card: nueva empresa */}
          <div className="bg-white rounded-2xl shadow-md p-6 flex flex-col items-center text-center">
            <div className="text-3xl mb-3">🏢</div>
            <h2 className="text-lg font-semibold text-gray-800 mb-1">¿Primera vez aquí?</h2>
            <p className="text-sm text-gray-500 mb-4">
              Crea el espacio de trabajo de tu empresa. Prueba gratuita por 14 días.
            </p>
            <Link
              to="/register"
              className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white text-center hover:bg-blue-700 transition-colors"
            >
              Registrar mi empresa
            </Link>
          </div>

          {/* Card: ya tiene cuenta */}
          <div className="bg-white rounded-2xl shadow-md p-6 flex flex-col">
            <div className="text-3xl mb-3 text-center">🔑</div>
            <h2 className="text-lg font-semibold text-gray-800 mb-1 text-center">¿Ya tienes cuenta?</h2>
            <p className="text-sm text-gray-500 mb-4 text-center">
              Ingresa el subdominio de tu empresa para acceder.
            </p>
            <form onSubmit={handleAccess} className="space-y-3">
              <div className="flex items-center rounded-lg border border-gray-300 shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-blue-500">
                <input
                  type="text"
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                  placeholder="mi-empresa"
                  className="flex-1 px-3 py-2 text-sm focus:outline-none"
                />
                <span className="px-3 py-2 bg-gray-50 text-gray-400 text-xs border-l border-gray-300 select-none whitespace-nowrap">
                  .sgca.com
                </span>
              </div>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button
                type="submit"
                className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
              >
                Ir a mi espacio
              </button>
            </form>
          </div>
        </div>
      </main>

      <footer className="text-center py-4 text-xs text-gray-400">
        © {new Date().getFullYear()} SGCA — Todos los derechos reservados
      </footer>
    </div>
  )
}
