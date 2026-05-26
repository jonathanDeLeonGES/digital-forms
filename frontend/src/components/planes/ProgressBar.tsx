interface ProgressBarProps {
  progreso: number
}

export function ProgressBar({ progreso }: ProgressBarProps) {
  const color = progreso === 100 ? 'bg-green-500' : progreso > 50 ? 'bg-blue-500' : 'bg-yellow-400'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-200 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-2.5 rounded-full transition-all duration-300 ${color}`}
          style={{ width: `${progreso}%` }}
        />
      </div>
      <span className="text-sm font-semibold text-gray-700 w-10 text-right">{progreso}%</span>
    </div>
  )
}
