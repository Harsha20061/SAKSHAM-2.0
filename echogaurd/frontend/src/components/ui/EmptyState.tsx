import React from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  Icon?: React.ComponentType<{ className?: string }>;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  Icon,
  className = '',
}) => (
  <div
    className={`flex flex-col items-center justify-center py-12 ${className}`}
    role="status"
    aria-live="polite"
  >
    {Icon && <Icon className="h-12 w-12 mb-4 text-[var(--color-primary)]" />}
    <h2 className="text-xl font-semibold text-[var(--color-primary)] mb-2">{title}</h2>
    {description && <p className="text-sm text-[var(--color-muted)]">{description}</p>}
  </div>
);
