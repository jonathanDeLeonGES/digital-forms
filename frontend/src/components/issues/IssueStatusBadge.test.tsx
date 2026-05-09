import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IssueStatusBadge } from './IssueStatusBadge'

describe('IssueStatusBadge', () => {
  it.each([
    ['abierto', 'Abierto'],
    ['en_analisis', 'En Análisis'],
    ['acciones_generadas', 'Acciones Generadas'],
    ['cerrado', 'Cerrado'],
  ])('muestra el label correcto para estado %s', (estado, label) => {
    render(<IssueStatusBadge estado={estado} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('muestra el estado raw para estados desconocidos', () => {
    render(<IssueStatusBadge estado="desconocido" />)
    expect(screen.getByText('desconocido')).toBeInTheDocument()
  })

  it('aplica clase de color azul para abierto', () => {
    render(<IssueStatusBadge estado="abierto" />)
    const badge = screen.getByText('Abierto')
    expect(badge.className).toMatch(/blue/)
  })

  it('aplica clase de color verde para cerrado', () => {
    render(<IssueStatusBadge estado="cerrado" />)
    const badge = screen.getByText('Cerrado')
    expect(badge.className).toMatch(/green/)
  })
})
