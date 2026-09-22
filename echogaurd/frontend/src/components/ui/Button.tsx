import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Variant determines styling. Options: 'primary', 'secondary', 'danger', 'outline'.
   */
  variant?: 'primary' | 'secondary' | 'danger' | 'outline';
  /**
   * When true, renders a loading spinner inside the button.
   */
  loading?: boolean;
}

/**
 * Reusable button component for the Saksham 2.0 interface.
 * Uses Tailwind CSS utilities for color, spacing and transitions.
 * Accessible: includes focus-visible outline and aria-busy when loading.
 */
export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  loading = false,
  disabled,
  children,
  className = '',
  ...rest
}) => {
  const baseClasses =
    'inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:pointer-events-none';

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'border border-slate-200 bg-white text-slate-900 hover:bg-slate-50',
    danger: 'bg-red-600 text-white hover:bg-red-500',
    outline: 'border border-slate-300 bg-white text-slate-900 hover:bg-blue-50',
  }[variant];

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${className}`}
      disabled={disabled || loading}
      aria-busy={loading}
      {...rest}
    >
      {loading && (
        <svg
          className="mr-2 h-4 w-4 animate-spin text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v8z"
          ></path>
        </svg>
      )}
      {children}
    </button>
  );
};
