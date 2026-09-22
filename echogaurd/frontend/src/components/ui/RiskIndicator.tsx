import React from 'react';
import { Badge } from './Badge';

/**
 * RiskIndicator – visual representation of a security risk level.
 * Supports three levels with distinct colors that map to the design palette:
 *   low        → green (success)
 *   suspicious → amber (warning)
 *   high       → red   (danger)
 */
interface RiskIndicatorProps {
  /** Risk level – determines the visual styling */
  level: 'low' | 'suspicious' | 'high';
  /** Optional textual description shown next to the badge */
  label?: string;
  /** Additional Tailwind classes for the root element */
  className?: string;
}

export const RiskIndicator: React.FC<RiskIndicatorProps> = ({
  level,
  label,
  className = '',
}) => {
  const variantMap = {
    low: 'success',
    suspicious: 'warning',
    high: 'danger',
  } as const;

  const badge = (
    <Badge variant={variantMap[level]} className="mr-2">
      {level}
    </Badge>
  );

  return (
    <div className={`flex items-center ${className}`} aria-label={`Risk level: ${level}`}>
      {badge}
      {label && (
        <span className="text-sm text-[var(--color-muted)]">{label}</span>
      )}
    </div>
  );
};
