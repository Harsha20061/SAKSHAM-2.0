interface AnalysisMetricProps {
  label: string
  value: number
}

export default function AnalysisMetric({
  label,
  value,
}: AnalysisMetricProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-400">
          {label}
        </span>

        <span className="font-semibold presentation-surface-text">
          {Math.round(value * 100)}%
        </span>
      </div>

      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-cyan-400 transition-all duration-500"
          style={{
            width: `${Math.round(value * 100)}%`,
          }}
        />
      </div>
    </div>
  )
}