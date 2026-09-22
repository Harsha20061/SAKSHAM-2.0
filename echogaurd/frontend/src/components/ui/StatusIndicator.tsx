import React from 'react';

interface StatusIndicatorProps {
  /** Status string – determines color */
  status: 'online' | 'offline' | 'active' | 'inactive' | 'error';
  /** Optional text label */
  label?: string;
  /** Size in pixels for the dot */
  size?: number;
  /** Additional Tailwind classes */
  className?: string;
}

/**
 * Small status indicator with a colored dot and optional label.
 * Uses CSS variables for colors to stay consistent with the theme.
 */
export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  label,
  size = 10,
  className = '',
}) => {
  const colorClass = {
    online: 'bg-[var(--color-success)]',
    offline: 'bg-gray-500',
    active: 'bg-[var(--color-primary)]',
    inactive: 'bg-gray-600',
    error: 'bg-[var(--color-danger)]',
  }[status];

  const dotStyle = {
    width: `${size}px`,
    height: `${size}px`,
  } as React.CSSProperties;

  return (
    <div className={`flex items-center ${className}`}>
      <span
        className={`inline-block rounded-full ${colorClass}`}
        style={dotStyle}
        aria-label={status}
      />
      {label && <span className="ml-2 text-sm text-slate-200">{label}</span>}
    </div>
  );
};
