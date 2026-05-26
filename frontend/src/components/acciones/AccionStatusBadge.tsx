const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  abierto: { label: 'Abierto', className: 'bg-gray-100 text-gray-800' },
  en_proceso: { label: 'En Proceso', className: 'bg-blue-100 text-blue-800' },
  cerrado: { label: 'Cerrado', className: 'bg-yellow-100 text-yellow-800' },
  verificado: { label: 'Verificado', className: 'bg-green-100 text-green-800' },
}

export function AccionStatusBadge({ estado }: { estado: string }) {
  const config = STATUS_CONFIG[estado] ?? { label: estado, className: 'bg-gray-100 text-gray-800' }
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  )
}
