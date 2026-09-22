import React from 'react';
import { Badge } from './Badge';

export type SecurityTimelineRisk = 'LOW' | 'SUSPICIOUS' | 'HIGH';

export interface SecurityTimelineEvent {
  id: string;
  time: string;
  label: string;
  risk: SecurityTimelineRisk;
  description?: string;
}

interface SecurityTimelineProps {
  events: SecurityTimelineEvent[];
  className?: string;
}

const riskVariant = {
  LOW: 'success',
  SUSPICIOUS: 'warning',
  HIGH: 'danger',
} as const;

export const SecurityTimeline: React.FC<SecurityTimelineProps> = ({
  events,
  className = '',
}) => {
  if (events.length === 0) {
    return (
      <div className={`py-8 text-center text-slate-400 ${className}`}>No security events yet.</div>
    );
  }

  return (
    <ul className={`space-y-4 ${className}`}>
      {events.map((event) => (
        <li key={event.id} className="relative border-l border-[var(--color-muted)] pl-6">
          <span
            className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-[var(--color-primary)]"
            aria-hidden="true"
          />
          <div className="flex flex-wrap items-center gap-2">
            <time className="text-xs text-slate-500">{event.time}</time>
            <span className="text-sm font-medium text-slate-200">{event.label}</span>
            <Badge variant={riskVariant[event.risk]}>{event.risk}</Badge>
          </div>
          {event.description && (
            <p className="mt-1 text-sm text-slate-400">{event.description}</p>
          )}
        </li>
      ))}
    </ul>
  );
};

export default SecurityTimeline;
