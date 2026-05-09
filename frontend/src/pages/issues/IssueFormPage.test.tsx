import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import IssueFormPage from './IssueFormPage'

vi.mock('../../services/issues', () => ({
  issuesService: {
    createIssue: vi.fn(),
    getIssue: vi.fn(),
    updateIssue: vi.fn(),
  },
}))

import { issuesService } from '../../services/issues'

const mockCreate = issuesService.createIssue as ReturnType<typeof vi.fn>
const mockGetIssue = issuesService.getIssue as ReturnType<typeof vi.fn>

function makeDetail(overrides = {}) {
  return {
    id: 1,
    tipo: 'incidente',
    titulo: 'Test Issue',
    descripcion: 'Descripción test',
    area: 'Planta',
    gravedad: 'alta',
    estado: 'abierto',
    reportado_por: { id: 1, nombre_completo: 'Admin' },
    fecha_evento: '2026-01-15',
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
    ishikawa: null,
    historial_estados: [],
    ...overrides,
  }
}

function renderCreate() {
  return render(
    <MemoryRouter initialEntries={['/issues/new']}>
      <Routes>
        <Route path="/issues/new" element={<IssueFormPage />} />
        <Route path="/issues/:id" element={<div>Detalle del issue</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderEdit(id = 1) {
  return render(
    <MemoryRouter initialEntries={[`/issues/${id}/edit`]}>
      <Routes>
        <Route path="/issues/:id/edit" element={<IssueFormPage />} />
        <Route path="/issues/:id" element={<div>Detalle del issue</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('IssueFormPage — creación', () => {
  it('muestra el formulario de creación', () => {
    renderCreate()
    expect(screen.getByLabelText(/título/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/descripción/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/área/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/tipo/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/gravedad/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/fecha del evento/i)).toBeInTheDocument()
  })

  it('muestra la sección de Ishikawa', () => {
    renderCreate()
    expect(screen.getByText(/ishikawa/i)).toBeInTheDocument()
    expect(screen.getByText('Método')).toBeInTheDocument()
  })

  it('envía POST y redirige al detalle en creación exitosa', async () => {
    mockCreate.mockResolvedValue(makeDetail())
    renderCreate()

    await userEvent.type(screen.getByLabelText(/título/i), 'Accidente')
    await userEvent.type(screen.getByLabelText(/descripción/i), 'Descripción')
    await userEvent.type(screen.getByLabelText(/área/i), 'Planta')
    await userEvent.selectOptions(screen.getByLabelText(/tipo/i), 'incidente')
    await userEvent.selectOptions(screen.getByLabelText(/gravedad/i), 'alta')
    await userEvent.type(screen.getByLabelText(/fecha del evento/i), '2026-01-15')

    await userEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByText('Detalle del issue')).toBeInTheDocument()
    })
  })

  it('muestra error de validación si título está vacío', async () => {
    renderCreate()
    await userEvent.click(screen.getByRole('button', { name: /guardar/i }))
    expect(mockCreate).not.toHaveBeenCalled()
    expect(screen.getByText(/título es requerido/i)).toBeInTheDocument()
  })
})

describe('IssueFormPage — edición', () => {
  it('carga los datos del issue para edición', async () => {
    mockGetIssue.mockResolvedValue(makeDetail())
    renderEdit(1)
    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Issue')).toBeInTheDocument()
    })
  })
})
