import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import IshikawaForm from './IshikawaForm'

function renderForm(onChange = vi.fn()) {
  return render(<IshikawaForm value={{}} onChange={onChange} />)
}

describe('IshikawaForm — estructura', () => {
  it('muestra las 6 categorías del Ishikawa', () => {
    renderForm()
    expect(screen.getByText('Método')).toBeInTheDocument()
    expect(screen.getByText('Máquina')).toBeInTheDocument()
    expect(screen.getByText('Material')).toBeInTheDocument()
    expect(screen.getByText('Mano de Obra')).toBeInTheDocument()
    expect(screen.getByText('Medición')).toBeInTheDocument()
    expect(screen.getByText('Medio Ambiente')).toBeInTheDocument()
  })

  it('muestra botón Agregar causa por cada categoría', () => {
    renderForm()
    const buttons = screen.getAllByRole('button', { name: /agregar causa/i })
    expect(buttons).toHaveLength(6)
  })
})

describe('IshikawaForm — agregar causas', () => {
  it('agrega un campo de causa al hacer clic en Agregar causa', async () => {
    renderForm()
    const [firstAddBtn] = screen.getAllByRole('button', { name: /agregar causa/i })
    await userEvent.click(firstAddBtn)
    expect(screen.getByPlaceholderText(/descripción de la causa/i)).toBeInTheDocument()
  })

  it('llama a onChange al agregar una causa', async () => {
    const onChange = vi.fn()
    renderForm(onChange)
    const [firstAddBtn] = screen.getAllByRole('button', { name: /agregar causa/i })
    await userEvent.click(firstAddBtn)
    expect(onChange).toHaveBeenCalled()
  })
})

describe('IshikawaForm — agregar subcausas', () => {
  it('muestra botón Agregar subcausa después de agregar una causa', async () => {
    renderForm()
    const [firstAddBtn] = screen.getAllByRole('button', { name: /agregar causa/i })
    await userEvent.click(firstAddBtn)
    expect(screen.getByRole('button', { name: /agregar subcausa/i })).toBeInTheDocument()
  })

  it('agrega campo de subcausa al hacer clic en Agregar subcausa', async () => {
    renderForm()
    const [firstAddBtn] = screen.getAllByRole('button', { name: /agregar causa/i })
    await userEvent.click(firstAddBtn)
    await userEvent.click(screen.getByRole('button', { name: /agregar subcausa/i }))
    expect(screen.getByPlaceholderText(/descripción de la subcausa/i)).toBeInTheDocument()
  })
})

describe('IshikawaForm — valor inicial', () => {
  it('muestra causas preexistentes cuando recibe value', () => {
    const onChange = vi.fn()
    render(
      <IshikawaForm
        value={{
          metodo: [{ descripcion: 'Causa preexistente', subcausas: [] }],
        }}
        onChange={onChange}
      />,
    )
    expect(screen.getByDisplayValue('Causa preexistente')).toBeInTheDocument()
  })
})
