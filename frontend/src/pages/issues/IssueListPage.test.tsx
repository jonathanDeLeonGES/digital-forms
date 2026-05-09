import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import IssueListPage from './IssueListPage'

vi.mock('../../services/issues', () => ({
  issuesService: {
    getIssues: vi.fn(),
  },
}))

import { issuesService } from '../../services/issues'

const mockGetIssues = issuesService.getIssues as ReturnType<typeof vi.fn>

function makeIssue(overrides = {}) {
  return {
    id: 1,
    tipo: 'incidente',
    titulo: 'Accidente en planta',
    area: 'Producción',
    gravedad: 'alta',
    estado: 'abierto',
    reportado_por: 1,
    fecha_evento: '2026-01-15',
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

function makePage(count = 1, issues = [makeIssue()]) {
  return { count, next: null, previous: null, results: issues }
}

function renderPage() {
  return render(
    <MemoryRouter>
      <IssueListPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockGetIssues.mockResolvedValue(makePage())
})

describe('IssueListPage — carga y listado', () => {
  it('muestra el título de la página', async () => {
    renderPage()
    expect(screen.getByText(/issues/i)).toBeInTheDocument()
  })

  it('muestra los issues recibidos del servicio', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Accidente en planta')).toBeInTheDocument()
    })
  })

  it('muestra badge de estado para cada issue', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Abierto')).toBeInTheDocument()
    })
  })

  it('muestra la gravedad del issue', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/alta/i)).toBeInTheDocument()
    })
  })

  it('muestra el área del issue', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Producción')).toBeInTheDocument()
    })
  })

  it('llama a getIssues al montar', async () => {
    renderPage()
    await waitFor(() => {
      expect(mockGetIssues).toHaveBeenCalledTimes(1)
    })
  })
})

describe('IssueListPage — filtros', () => {
  it('renderiza selector de estado', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.getByRole('combobox', { name: /estado/i })).toBeInTheDocument()
  })

  it('renderiza selector de tipo', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.getByRole('combobox', { name: /tipo/i })).toBeInTheDocument()
  })

  it('renderiza selector de gravedad', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.getByRole('combobox', { name: /gravedad/i })).toBeInTheDocument()
  })

  it('llama a getIssues con filtro de estado al cambiar el selector', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    mockGetIssues.mockResolvedValueOnce(makePage(0, []))

    await userEvent.selectOptions(screen.getByRole('combobox', { name: /estado/i }), 'cerrado')

    await waitFor(() => {
      expect(mockGetIssues).toHaveBeenCalledWith(expect.objectContaining({ estado: 'cerrado' }))
    })
  })
})

describe('IssueListPage — paginación', () => {
  it('muestra botón Siguiente si hay más páginas', async () => {
    mockGetIssues.mockResolvedValue({
      count: 25,
      next: '/api/issues/?page=2',
      previous: null,
      results: [makeIssue()],
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /siguiente/i })).toBeInTheDocument()
    })
  })

  it('no muestra botón Siguiente cuando no hay más páginas', async () => {
    mockGetIssues.mockResolvedValue(makePage(1))
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.queryByRole('button', { name: /siguiente/i })).not.toBeInTheDocument()
  })
})

describe('IssueListPage — enlace a detalle', () => {
  it('muestra enlace para ver el detalle del issue', async () => {
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    const links = screen.getAllByRole('link')
    expect(links.some((l) => l.getAttribute('href')?.includes('/issues/1'))).toBe(true)
  })
})
