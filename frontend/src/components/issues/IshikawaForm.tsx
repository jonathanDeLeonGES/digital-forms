import { useState } from 'react'

const CATEGORIAS = [
  { key: 'metodo', label: 'Método' },
  { key: 'maquina', label: 'Máquina' },
  { key: 'material', label: 'Material' },
  { key: 'mano_de_obra', label: 'Mano de Obra' },
  { key: 'medicion', label: 'Medición' },
  { key: 'medio_ambiente', label: 'Medio Ambiente' },
]

export interface CausaEntry {
  descripcion: string
  subcausas: Array<{ descripcion: string }>
}

export type IshikawaValue = Record<string, CausaEntry[]>

interface Props {
  value: IshikawaValue
  onChange: (value: IshikawaValue) => void
}

export default function IshikawaForm({ value, onChange }: Props) {
  // Internal state so user interactions re-render without needing parent to propagate value back
  const [state, setState] = useState<IshikawaValue>(() => value ?? {})
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({})

  function update(newState: IshikawaValue) {
    setState(newState)
    onChange(newState)
  }

  function toggleCategory(key: string) {
    setOpenCategories((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function getCausas(cat: string): CausaEntry[] {
    return state[cat] ?? []
  }

  function addCausa(cat: string) {
    const causas = [...getCausas(cat), { descripcion: '', subcausas: [] }]
    update({ ...state, [cat]: causas })
    setOpenCategories((prev) => ({ ...prev, [cat]: true }))
  }

  function updateCausa(cat: string, idx: number, descripcion: string) {
    const causas = getCausas(cat).map((c, i) => (i === idx ? { ...c, descripcion } : c))
    update({ ...state, [cat]: causas })
  }

  function removeCausa(cat: string, idx: number) {
    const causas = getCausas(cat).filter((_, i) => i !== idx)
    update({ ...state, [cat]: causas })
  }

  function addSubcausa(cat: string, causaIdx: number) {
    const causas = getCausas(cat).map((c, i) =>
      i === causaIdx ? { ...c, subcausas: [...c.subcausas, { descripcion: '' }] } : c,
    )
    update({ ...state, [cat]: causas })
  }

  function updateSubcausa(cat: string, causaIdx: number, subIdx: number, descripcion: string) {
    const causas = getCausas(cat).map((c, ci) =>
      ci === causaIdx
        ? { ...c, subcausas: c.subcausas.map((s, si) => (si === subIdx ? { descripcion } : s)) }
        : c,
    )
    update({ ...state, [cat]: causas })
  }

  function removeSubcausa(cat: string, causaIdx: number, subIdx: number) {
    const causas = getCausas(cat).map((c, ci) =>
      ci === causaIdx ? { ...c, subcausas: c.subcausas.filter((_, si) => si !== subIdx) } : c,
    )
    update({ ...state, [cat]: causas })
  }

  return (
    <div className="space-y-3">
      {CATEGORIAS.map(({ key, label }) => {
        const causas = getCausas(key)
        const isOpen = openCategories[key] ?? causas.length > 0

        return (
          <div key={key} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between bg-gray-50 px-4 py-3">
              <button
                type="button"
                onClick={() => toggleCategory(key)}
                className="flex-1 flex items-center gap-2 text-left text-sm font-semibold text-gray-700"
              >
                <span>{isOpen ? '▼' : '▶'}</span>
                {label}
                {causas.length > 0 && (
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    ({causas.length} causa{causas.length !== 1 ? 's' : ''})
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => addCausa(key)}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium px-2 py-1 rounded hover:bg-blue-50"
              >
                + Agregar causa
              </button>
            </div>

            {isOpen && (
              <div className="p-3 space-y-3">
                {causas.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-2">
                    No hay causas registradas. Haga clic en &quot;Agregar causa&quot; para añadir.
                  </p>
                ) : (
                  causas.map((causa, causaIdx) => (
                    <div key={causaIdx} className="bg-white border border-gray-200 rounded-lg p-3">
                      <div className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={causa.descripcion}
                          onChange={(e) => updateCausa(key, causaIdx, e.target.value)}
                          placeholder="Descripción de la causa"
                          className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button
                          type="button"
                          onClick={() => removeCausa(key, causaIdx)}
                          className="text-xs text-red-500 hover:text-red-700 px-2"
                          title="Eliminar causa"
                        >
                          ✕
                        </button>
                      </div>

                      {causa.subcausas.map((sub, subIdx) => (
                        <div key={subIdx} className="flex gap-2 mb-1 ml-4">
                          <span className="text-gray-400 text-xs mt-2">↳</span>
                          <input
                            type="text"
                            value={sub.descripcion}
                            onChange={(e) => updateSubcausa(key, causaIdx, subIdx, e.target.value)}
                            placeholder="Descripción de la subcausa"
                            className="flex-1 rounded border border-gray-200 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                          />
                          <button
                            type="button"
                            onClick={() => removeSubcausa(key, causaIdx, subIdx)}
                            className="text-xs text-red-400 hover:text-red-600"
                            title="Eliminar subcausa"
                          >
                            ✕
                          </button>
                        </div>
                      ))}

                      <button
                        type="button"
                        onClick={() => addSubcausa(key, causaIdx)}
                        className="ml-4 mt-1 text-xs text-blue-500 hover:text-blue-700"
                      >
                        + Agregar subcausa
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
