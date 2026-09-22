import React from 'react';

interface ProgressBarProps {
  /** Percentage value (0-100). Values outside this range will be clamped. */
  percentage: number;
  /** Variant determines the bar color. Defaults to primary (cyan). */
  variant?: 'default' | 'success' | 'warning' | 'danger';
  /** Additional class names for the container */
  className?: string;
  /** Accessible label describing what the progress represents */
  label?: string;
}

/**
 * Horizontal progress bar component.
 * Uses Tailwind utilities and CSS variables for colors.
 * Accessible via ARIA attributes.
 */
export const ProgressBar: React.FC<ProgressBarProps> = ({
  percentage,
  variant = 'default',
  className = '',
  label = 'Progress',
}) => {
  const clamped = Math.min(100, Math.max(0, percentage));
  const bgClass = {
    default: 'bg-[var(--color-primary)]',
    success: 'bg-[var(--color-success)]',
    warning: 'bg-[var(--color-warning)]',
    danger: 'bg-[var(--color-danger)]',
  }[variant];

  return (
    <div
      className={`w-full rounded-full bg-slate-700 h-2 overflow-hidden ${className}`}
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={`${bgClass} h-full`}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
};
