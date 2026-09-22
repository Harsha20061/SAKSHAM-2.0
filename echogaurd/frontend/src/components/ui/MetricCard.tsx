import React from 'react';

interface MetricCardProps {
  /** Title of the metric, e.g., 'Calls Detected' */
  title: string;
  /** Value to display, can be string or number */
  value: string | number;
  /** Optional variant for coloring the value */
  variant?: 'default' | 'success' | 'warning' | 'danger';
  /** Optional icon component from lucide-react */
  Icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  /** Additional Tailwind classes for the container */
  className?: string;
}

/** Small card used to display a single numeric or textual metric. */
export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  variant = 'default',
  Icon,
  className = '',
}) => {
  const valueClass = {
    default: 'text-[var(--color-primary)]',
    success: 'text-[var(--color-success)]',
    warning: 'text-[var(--color-warning)]',
    danger: 'text-[var(--color-danger)]',
  }[variant];

  return (
    <div className={`flex items-center rounded-lg bg-[var(--color-surface)] p-4 shadow-sm ${className}`}>
      {Icon && (
        <Icon className="h-6 w-6 mr-3 text-[var(--color-muted)] flex-shrink-0" aria-hidden="true" />
      )}
      <div className="flex flex-col">
        <span className="text-sm text-[var(--color-muted)]">{title}</span>
        <span className={`text-2xl font-semibold ${valueClass}`}>{value}</span>
      </div>
    </div>
  );
};
