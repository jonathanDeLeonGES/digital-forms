import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import RegisterPage from './RegisterPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <RegisterPage />
    </MemoryRouter>,
  )
}

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockReset()
})

/** Fills all required fields except those in `skip`. */
async function fillForm(skip: Array<keyof typeof fields> = []) {
  const fields = {
    nombre_empresa: { label: /nombre de empresa/i, value: 'ACME S.A.' },
    subdominio:     { label: /subdominio/i,         value: 'acme' },
    email_admin:    { label: /email/i,              value: 'admin@acme.com' },
    password:       { label: /contraseña/i,         value: 'Admin123!' },
  }
  for (const [key, { label, value }] of Object.entries(fields)) {
    if (!skip.includes(key as keyof typeof fields)) {
      await userEvent.type(screen.getByLabelText(label), value)
    }
  }
}

describe('RegisterPage — validación client-side', () => {
  it('muestra error si nombre_empresa está vacío', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))
    expect(screen.getByText('El nombre de empresa es requerido.')).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('muestra error si subdominio está vacío', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText(/nombre de empresa/i), 'ACME')
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))
    expect(screen.getByText('El subdominio es requerido.')).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('muestra error si subdominio tiene formato inválido', async () => {
    renderPage()
    await userEvent.type(screen.getByLabelText(/nombre de empresa/i), 'ACME')
    await userEvent.type(screen.getByLabelText(/subdominio/i), '-acme')
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@acme.com')
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'Admin123!')
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))
    expect(screen.getByText(/solo puede contener/i)).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('muestra error si email es inválido', async () => {
    renderPage()
    await fillForm(['email_admin'])
    await userEvent.type(screen.getByLabelText(/email/i), 'no-es-email')
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))
    expect(screen.getByText('Ingrese un email válido.')).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('muestra error si password está vacía', async () => {
    renderPage()
    await fillForm(['password'])
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))
    expect(screen.getByText('La contraseña es requerida.')).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('muestra error si password tiene menos de 8 caracteres', async () => {
    renderPage()
    await fillForm(['password'])
    await userEvent.type(screen.getByLabelText(/contraseña/i), 'short')
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))
    expect(screen.getByText('La contraseña debe tener al menos 8 caracteres.')).toBeInTheDocument()
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('normaliza el subdominio a minúsculas automáticamente', async () => {
    renderPage()
    const subdominioInput = screen.getByLabelText(/subdominio/i)
    await userEvent.type(subdominioInput, 'ACME')
    expect((subdominioInput as HTMLInputElement).value).toBe('acme')
  })
})

describe('RegisterPage — respuestas del servidor', () => {
  it('muestra el mensaje de éxito y la URL del tenant en registro exitoso (201)', async () => {
    mockFetch.mockResolvedValueOnce({
      status: 201,
      json: async () => ({
        id: 1,
        subdominio: 'acme',
        trial_expires_at: '2026-05-22T00:00:00Z',
        message: 'Tenant registrado con éxito.',
      }),
    })

    renderPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))

    await waitFor(() => {
      expect(screen.getByText('¡Registro exitoso!')).toBeInTheDocument()
    })
    expect(screen.getByText('acme.sgca.com')).toBeInTheDocument()
  })

  it('envía password en el body del request', async () => {
    mockFetch.mockResolvedValueOnce({
      status: 201,
      json: async () => ({ id: 1, subdominio: 'acme', trial_expires_at: '2026-05-22T00:00:00Z', message: '' }),
    })

    renderPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))

    await waitFor(() => expect(mockFetch).toHaveBeenCalled())
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.password).toBe('Admin123!')
  })

  it('muestra errores por campo en respuesta 400', async () => {
    mockFetch.mockResolvedValueOnce({
      status: 400,
      json: async () => ({
        subdominio: ['El subdominio tiene un formato inválido.'],
      }),
    })

    renderPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))

    await waitFor(() => {
      expect(screen.getByText('El subdominio tiene un formato inválido.')).toBeInTheDocument()
    })
  })

  it('muestra error global en respuesta 409 (subdominio duplicado)', async () => {
    mockFetch.mockResolvedValueOnce({
      status: 409,
      json: async () => ({
        detail: "El subdominio 'acme' ya está registrado.",
        code: 'subdomain_already_exists',
      }),
    })

    renderPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))

    await waitFor(() => {
      expect(screen.getByText(/ya está registrado/i)).toBeInTheDocument()
    })
  })

  it('muestra error genérico cuando fetch lanza excepción (sin conexión)', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    renderPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))

    await waitFor(() => {
      expect(screen.getByText(/no se pudo conectar/i)).toBeInTheDocument()
    })
  })

  it('deshabilita el botón mientras carga', async () => {
    let resolveResponse!: (value: unknown) => void
    mockFetch.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveResponse = resolve
      }),
    )

    renderPage()
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: /crear cuenta/i }))

    expect(screen.getByRole('button', { name: /registrando/i })).toBeDisabled()

    resolveResponse({
      status: 201,
      json: async () => ({ id: 1, subdominio: 'acme', trial_expires_at: '2026-05-22T00:00:00Z', message: '' }),
    })
  })
})
