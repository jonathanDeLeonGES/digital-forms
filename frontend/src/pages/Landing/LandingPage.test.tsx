import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LandingPage from './LandingPage'

// jsdom sets window.location.hostname = 'localhost' by default

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/register" element={<div>Página de registro</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('LandingPage — contenido', () => {
  it('muestra el nombre del producto', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: /SGCA/ })).toBeInTheDocument()
  })

  it('muestra enlace para registrar empresa', () => {
    renderPage()
    expect(screen.getByRole('link', { name: /registrar mi empresa/i })).toBeInTheDocument()
  })

  it('muestra campo para ingresar subdominio', () => {
    renderPage()
    expect(screen.getByPlaceholderText(/mi-empresa/i)).toBeInTheDocument()
  })

  it('muestra botón para acceder al espacio', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /ir a mi espacio/i })).toBeInTheDocument()
  })
})

describe('LandingPage — enlace a registro', () => {
  it('navega a /register al hacer clic en Registrar', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('link', { name: /registrar mi empresa/i }))
    expect(screen.getByText('Página de registro')).toBeInTheDocument()
  })
})

describe('LandingPage — acceso al tenant', () => {
  it('no navega si el subdominio está vacío', async () => {
    const assignSpy = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { ...window.location, assign: assignSpy, hostname: 'localhost', port: '5173', protocol: 'http:' },
      writable: true,
    })
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: /ir a mi espacio/i }))
    expect(assignSpy).not.toHaveBeenCalled()
  })

  it('navega a la URL correcta del tenant al ingresar subdominio', async () => {
    const assignSpy = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { hostname: 'localhost', port: '5173', protocol: 'http:', assign: assignSpy },
      writable: true,
    })
    renderPage()
    await userEvent.type(screen.getByPlaceholderText(/mi-empresa/i), 'acme')
    await userEvent.click(screen.getByRole('button', { name: /ir a mi espacio/i }))
    expect(assignSpy).toHaveBeenCalledWith('http://acme.localhost:5173/login')
  })

  it('normaliza el subdominio a minúsculas', async () => {
    const assignSpy = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { hostname: 'localhost', port: '5173', protocol: 'http:', assign: assignSpy },
      writable: true,
    })
    renderPage()
    await userEvent.type(screen.getByPlaceholderText(/mi-empresa/i), 'ACME')
    await userEvent.click(screen.getByRole('button', { name: /ir a mi espacio/i }))
    expect(assignSpy).toHaveBeenCalledWith('http://acme.localhost:5173/login')
  })
})
