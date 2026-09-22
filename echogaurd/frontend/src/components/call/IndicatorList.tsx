interface IndicatorListProps {
  indicators: string[]
}

function formatIndicator(
  indicator: string,
): string {
  return indicator
    .split('_')
    .map(
      (word) =>
        word.charAt(0).toUpperCase() +
        word.slice(1),
    )
    .join(' ')
}

export default function IndicatorList({
  indicators,
}: IndicatorListProps) {
  if (indicators.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No suspicious indicators detected.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {indicators.map((indicator) => (
        <div
          key={indicator}
          className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          <span>⚠</span>
          <span>
            {formatIndicator(indicator)}
          </span>
        </div>
      ))}
    </div>
  )
}