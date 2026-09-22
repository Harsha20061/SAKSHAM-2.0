import type { RiskLevel } from '../../types/analysis'

interface RiskBadgeProps {
  level: RiskLevel
}

export default function RiskBadge({
  level,
}: RiskBadgeProps) {
  const config = {
    LOW: {
      label: 'LOW RISK',
      className:
        'border-emerald-200 bg-emerald-50 text-emerald-700',
    },
    SUSPICIOUS: {
      label: 'SUSPICIOUS',
      className:
        'border-amber-200 bg-amber-50 text-amber-700',
    },
    HIGH: {
      label: 'HIGH RISK',
      className:
        'border-red-200 bg-red-50 text-red-700',
    },
  }

  const current = config[level]

  return (
    <div
      className={`rounded-xl border px-4 py-3 text-center font-bold ${current.className}`}
    >
      {current.label}
    </div>
  )
}