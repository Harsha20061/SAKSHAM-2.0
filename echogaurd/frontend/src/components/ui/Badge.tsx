import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Variant controls color. Options: 'success', 'warning', 'danger', 'neutral' */
  variant?: 'success' | 'warning' | 'danger' | 'neutral';
  /** Additional Tailwind classes */
  className?: string;
  /** Children (badge label) */
  children: React.ReactNode;
}

/**
 * Small badge used for status indicators.
 */
export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  className = '',
  children,
  ...rest
}) => {
  const variantClasses: Record<string, string> = {
    success: 'bg-[var(--color-success)] text-white',
    warning: 'bg-[var(--color-warning)] text-white',
    danger: 'bg-[var(--color-danger)] text-white',
    neutral: 'bg-[var(--color-muted)] text-white',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
      {...rest}
    >
      {children}
    </span>
  );
};
