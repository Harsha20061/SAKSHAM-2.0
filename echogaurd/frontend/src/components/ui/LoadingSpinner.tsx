import React from 'react';

interface LoadingSpinnerProps {
  className?: string;
}

/** Simple accessible loading spinner */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ className = '' }) => (
  <div
    className={`animate-spin rounded-full border-4 border-t-4 border-[var(--color-primary)] ${className}`}
    role="status"
    aria-label="Loading"
  />
);
