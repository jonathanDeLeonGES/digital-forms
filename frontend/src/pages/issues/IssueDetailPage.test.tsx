import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import IssueDetailPage from './IssueDetailPage'

vi.mock('../../services/issues', () => ({
  issuesService: {
    getIssue: vi.fn(),
    transitionIssue: vi.fn(),
  },
}))

import { issuesService } from '../../services/issues'

const mockGetIssue = issuesService.getIssue as ReturnType<typeof vi.fn>
const mockTransition = issuesService.transitionIssue as ReturnType<typeof vi.fn>

function makeDetail(overrides = {}) {
  return {
    id: 1,
    tipo: 'incidente',
    titulo: 'Accidente en planta',
    descripcion: 'Descripción detallada',
    area: 'Producción',
    gravedad: 'alta',
    estado: 'abierto',
    reportado_por: { id: 1, nombre_completo: 'Juan Pérez' },
    fecha_evento: '2026-01-15',
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
    ishikawa: null,
    historial_estados: [],
    ...overrides,
  }
}

function renderPage(id = 1, userRole = 'admin') {
  localStorage.setItem('user', JSON.stringify({ id: 1, role: userRole }))
  return render(
    <MemoryRouter initialEntries={[`/issues/${id}`]}>
      <Routes>
        <Route path="/issues/:id" element={<IssueDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
})

describe('IssueDetailPage — carga de datos', () => {
  it('muestra el título del issue', async () => {
    mockGetIssue.mockResolvedValue(makeDetail())
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Accidente en planta')).toBeInTheDocument()
    })
  })

  it('muestra el estado con badge coloreado', async () => {
    mockGetIssue.mockResolvedValue(makeDetail())
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Abierto')).toBeInTheDocument()
    })
  })

  it('muestra la descripción del issue', async () => {
    mockGetIssue.mockResolvedValue(makeDetail())
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Descripción detallada')).toBeInTheDocument()
    })
  })

  it('muestra el nombre del reportante', async () => {
    mockGetIssue.mockResolvedValue(makeDetail())
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Juan Pérez')).toBeInTheDocument()
    })
  })
})

describe('IssueDetailPage — transiciones de estado', () => {
  it('muestra botón de transición para admin en estado abierto', async () => {
    mockGetIssue.mockResolvedValue(makeDetail({ estado: 'abierto' }))
    renderPage(1, 'admin')
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /en análisis/i })).toBeInTheDocument()
    })
  })

  it('no muestra botones de transición para verificador', async () => {
    mockGetIssue.mockResolvedValue(makeDetail({ estado: 'abierto' }))
    renderPage(1, 'verificador')
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.queryByRole('button', { name: /en análisis/i })).not.toBeInTheDocument()
  })

  it('llama a transitionIssue al hacer clic en botón de transición', async () => {
    mockGetIssue.mockResolvedValue(makeDetail({ estado: 'abierto' }))
    mockTransition.mockResolvedValue(makeDetail({ estado: 'en_analisis' }))
    renderPage(1, 'admin')
    await waitFor(() => screen.getByRole('button', { name: /en análisis/i }))
    await userEvent.click(screen.getByRole('button', { name: /en análisis/i }))
    await waitFor(() => {
      expect(mockTransition).toHaveBeenCalledWith(1, 'en_analisis', '')
    })
  })
})

describe('IssueDetailPage — Ishikawa', () => {
  it('muestra el Ishikawa si existe', async () => {
    mockGetIssue.mockResolvedValue(
      makeDetail({
        ishikawa: {
          id: 1,
          issue: 1,
          categorias: {
            metodo: [{ id: 1, categoria: 'metodo', descripcion: 'Proc. obsoleto', subcausas: [] }],
            maquina: [],
            material: [],
            mano_de_obra: [],
            medicion: [],
            medio_ambiente: [],
          },
        },
      }),
    )
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Proc. obsoleto')).toBeInTheDocument()
    })
  })

  it('no muestra sección Ishikawa si es null', async () => {
    mockGetIssue.mockResolvedValue(makeDetail({ ishikawa: null }))
    renderPage()
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.queryByText('Proc. obsoleto')).not.toBeInTheDocument()
  })
})

describe('IssueDetailPage — historial de estados', () => {
  it('muestra historial para admin', async () => {
    mockGetIssue.mockResolvedValue(
      makeDetail({
        historial_estados: [
          {
            id: 1,
            estado_anterior: 'abierto',
            estado_nuevo: 'en_analisis',
            usuario: 1,
            timestamp: '2026-01-16T10:00:00Z',
            comentario: '',
          },
        ],
      }),
    )
    renderPage(1, 'admin')
    await waitFor(() => {
      expect(screen.getByText(/en_analisis/i)).toBeInTheDocument()
    })
  })

  it('no muestra historial para responsable', async () => {
    mockGetIssue.mockResolvedValue(
      makeDetail({
        historial_estados: [
          {
            id: 1,
            estado_anterior: 'abierto',
            estado_nuevo: 'en_analisis',
            usuario: 1,
            timestamp: '2026-01-16T10:00:00Z',
            comentario: '',
          },
        ],
      }),
    )
    renderPage(1, 'responsable')
    await waitFor(() => screen.getByText('Accidente en planta'))
    expect(screen.queryByText('Historial de estados')).not.toBeInTheDocument()
  })
})
