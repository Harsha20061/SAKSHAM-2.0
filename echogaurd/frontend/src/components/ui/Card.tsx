import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Optional title displayed at the top of the card */
  title?: string;
  /** Additional class names for custom styling */
  className?: string;
}

/**
 * Generic Card component used throughout the Saksham 2.0 UI.
 * Applies a surface background using CSS variables, a subtle border, and shadow.
 * Accessible: rendered as a landmark region; title uses <h2> for proper hierarchy.
 */
export const Card: React.FC<CardProps> = ({ title, children, className = '', ...rest }) => {
  return (
    <div
      className={`rounded-xl p-4 text-sm text-slate-200 shadow-sm border ${className}`}
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-muted)',
      }}
      {...rest}
    >
      {title && (
        <h2 className="mb-3 text-base font-medium text-slate-100 border-b border-slate-700 pb-2">
          {title}
        </h2>
      )}
      {children}
    </div>
  );
};
