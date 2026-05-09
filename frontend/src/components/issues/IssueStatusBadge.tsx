const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  abierto: { label: 'Abierto', className: 'bg-blue-100 text-blue-800' },
  en_analisis: { label: 'En Análisis', className: 'bg-yellow-100 text-yellow-800' },
  acciones_generadas: { label: 'Acciones Generadas', className: 'bg-orange-100 text-orange-800' },
  cerrado: { label: 'Cerrado', className: 'bg-green-100 text-green-800' },
}

export function IssueStatusBadge({ estado }: { estado: string }) {
  const config = STATUS_CONFIG[estado] ?? { label: estado, className: 'bg-gray-100 text-gray-800' }
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  )
}
