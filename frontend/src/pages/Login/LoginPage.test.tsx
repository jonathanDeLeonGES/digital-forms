import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LoginPage from './LoginPage'

vi.mock('../../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '../../context/AuthContext'

const mockUseAuth = useAuth as ReturnType<typeof vi.fn>

function makeAuth(overrides: Partial<ReturnType<typeof useAuth>> = {}) {
  return {
    user: null,
    isAuthenticated: false,
    login: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  }
}

function renderPage(auth = makeAuth()) {
  mockUseAuth.mockReturnValue(auth)
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/issues" element={<div>Página de issues</div>} />
        <Route path="/register" element={<div>Página de registro</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('LoginPage — estructura', () => {
  it('muestra campo de email', () => {
    renderPage()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
  })

  it('muestra campo de contraseña', () => {
    renderPage()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
  })

  it('muestra botón de ingresar', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument()
  })

  it('muestra enlace a registro de empresa', () => {
    renderPage()
    expect(screen.getByRole('link', { name: /regístrala aquí/i })).toBeInTheDocument()
  })
})

describe('LoginPage — validación', () => {
  it('no llama a login si el email está vacío', async () => {
    const auth = makeAuth()
    renderPage(auth)
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }))
    expect(auth.login).not.toHaveBeenCalled()
  })
})

describe('LoginPage — flujo de autenticación', () => {
  it('llama a login con email y password al hacer submit', async () => {
    const auth = makeAuth()
    renderPage(auth)
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@acme.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'Admin123!')
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }))
    await waitFor(() => {
      expect(auth.login).toHaveBeenCalledWith('admin@acme.com', 'Admin123!')
    })
  })

  it('redirige a /issues tras login exitoso', async () => {
    const auth = makeAuth({ login: vi.fn().mockResolvedValue(undefined) })
    renderPage(auth)
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@acme.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'Admin123!')
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }))
    await waitFor(() => {
      expect(screen.getByText('Página de issues')).toBeInTheDocument()
    })
  })

  it('muestra "Credenciales incorrectas." en error 401', async () => {
    const err = Object.assign(new Error('Unauthorized'), { status: 401 })
    const auth = makeAuth({ login: vi.fn().mockRejectedValue(err) })
    renderPage(auth)
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@acme.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }))
    await waitFor(() => {
      expect(screen.getByText('Credenciales incorrectas.')).toBeInTheDocument()
    })
  })

  it('muestra mensaje de conexión en error de red', async () => {
    const auth = makeAuth({ login: vi.fn().mockRejectedValue(new TypeError('Failed to fetch')) })
    renderPage(auth)
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@acme.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'Admin123!')
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }))
    await waitFor(() => {
      expect(screen.getByText(/no se pudo conectar/i)).toBeInTheDocument()
    })
  })

  it('deshabilita el botón mientras carga', async () => {
    let resolve!: () => void
    const auth = makeAuth({
      login: vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r })),
    })
    renderPage(auth)
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@acme.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'Admin123!')
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }))
    expect(screen.getByRole('button', { name: /ingresando/i })).toBeDisabled()
    resolve()
  })
})

describe('LoginPage — ya autenticado', () => {
  it('redirige a /issues si ya está autenticado', () => {
    renderPage(makeAuth({ isAuthenticated: true, user: { id: 1, email: 'a@b.com', role: 'admin', tenant: 'acme' } }))
    expect(screen.getByText('Página de issues')).toBeInTheDocument()
  })
})

describe('LoginPage — enlace a registro', () => {
  it('navega a /register al hacer clic en el enlace', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('link', { name: /regístrala aquí/i }))
    expect(screen.getByText('Página de registro')).toBeInTheDocument()
  })
})
