const CONFIG: Record<string, { label: string; classes: string }> = {
  pendiente:   { label: 'Pendiente',   classes: 'bg-gray-100 text-gray-700' },
  en_proceso:  { label: 'En Proceso',  classes: 'bg-blue-100 text-blue-700' },
  completada:  { label: 'Completada',  classes: 'bg-green-100 text-green-700' },
}

export function ActividadStatusBadge({ estado }: { estado: string }) {
  const { label, classes } = CONFIG[estado] ?? { label: estado, classes: 'bg-gray-100 text-gray-700' }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${classes}`}>
      {label}
    </span>
  )
}
