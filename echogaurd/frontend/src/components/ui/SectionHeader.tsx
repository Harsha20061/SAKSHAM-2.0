import React from 'react';

interface SectionHeaderProps {
  /** Main heading text */
  title: string;
  /** Optional sub‑heading or description */
  subtitle?: string;
  /** Optional actions (e.g., buttons) rendered on the right */
  actions?: React.ReactNode;
  /** Additional Tailwind classes */
  className?: string;
}

/**
 * SectionHeader – consistent heading block used across the dashboard.
 * Uses CSS‑variable based colors to match the dark security theme.
 */
export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  subtitle,
  actions,
  className = '',
}) => {
  return (
    <header
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 ${className}`}
    >
      <div>
        <h2 className="text-2xl font-semibold text-[var(--color-primary)]">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-1 text-sm text-[var(--color-muted)]">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
};
