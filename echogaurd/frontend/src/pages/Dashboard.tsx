import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  Clock3,
  Phone,
  ShieldAlert,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { useAuth } from '../context/useAuth'
import { getCalls } from '../services/calls'
import { getContacts } from '../services/contacts'
import { getCallSecurityReport } from '../services/calls'
import type { CallResponse, CallSecurityReport } from '../types/calls'

interface DashboardData {
  calls: CallResponse[]
  contacts: Awaited<ReturnType<typeof getContacts>>
  reports: CallSecurityReport[]
}

const pipeline = [
  ['CALL', 'Secure connection'],
  ['DETECT', 'AASIST voice authenticity'],
  ['VERIFY', 'ECAPA trusted speaker'],
  ['ASSESS', 'ASR + scam analysis'],
  ['RISK', 'Risk Engine'],
  ['INTERVENE', 'Actionable protection'],
] as const

function formatDuration(seconds: number) {
  if (seconds < 60) {
    return `${Math.round(seconds)} sec`
  }

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)

  return remainingSeconds === 0
    ? `${minutes} min`
    : `${minutes} min ${remainingSeconds} sec`
}

function callDuration(call: CallResponse) {
  if (!call.started_at || !call.ended_at) {
    return null
  }

  const duration = (Date.parse(call.ended_at) - Date.parse(call.started_at)) / 1000

  return Number.isFinite(duration) && duration >= 0 ? duration : null
}

function formatDate(value: string | null) {
  if (!value) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function reportForCall(
  call: CallResponse,
  reports: CallSecurityReport[],
) {
  return reports.find((report) => report.call_id === call.id)
}

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadDashboard() {
      try {
        setLoading(true)
        setError(null)

        const [calls, contacts] = await Promise.all([
          getCalls(),
          getContacts(),
        ])

        const endedCalls = calls.filter((call) => call.status === 'ENDED')
        const reportResults = await Promise.allSettled(
          endedCalls.map((call) => getCallSecurityReport(call.id)),
        )
        const reports = reportResults
          .filter(
            (result): result is PromiseFulfilledResult<CallSecurityReport> =>
              result.status === 'fulfilled',
          )
          .map((result) => result.value)

        if (!cancelled) {
          setData({ calls, contacts, reports })
        }
      } catch (loadError) {
        console.error('[Dashboard] Failed to load dashboard data:', loadError)

        if (!cancelled) {
          setError('Unable to load your security overview right now.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadDashboard()

    return () => {
      cancelled = true
    }
  }, [])

  const metrics = useMemo(() => {
    const calls = data?.calls ?? []
    const endedCalls = calls.filter((call) => call.status === 'ENDED')
    const totalSeconds = endedCalls.reduce(
      (total, call) => total + (callDuration(call) ?? 0),
      0,
    )
    const indicators = new Set(
      (data?.reports ?? []).flatMap((report) => report.indicators),
    )

    return {
      protectedCalls: endedCalls.length,
      threatsDetected: indicators.size,
      trustedContacts: data?.contacts.filter((contact) => contact.is_trusted).length ?? 0,
      totalSeconds,
      endedCalls,
      indicators: [...indicators],
    }
  }, [data])

  if (loading) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">
          Loading your security overview...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-[1400px] rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {error}
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-8">
      <section className="rounded-2xl border border-blue-100 bg-white p-7 shadow-sm lg:p-9">
        <div className="flex flex-col justify-between gap-8 lg:flex-row lg:items-center">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">
              Security overview
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
              Good morning, {user?.display_name || 'there'}
            </h1>
            <p className="mt-3 max-w-xl text-base leading-7 text-slate-600">
              Saksham 2.0 helps you identify voice impersonation and social-engineering threats before they become costly.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/contacts"
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
              >
                Start from Contacts
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/contacts"
                className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-blue-200 hover:bg-blue-50"
              >
                View Contacts
              </Link>
            </div>
          </div>

          <div className="max-w-sm rounded-xl border border-blue-100 bg-blue-50 p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-white p-2.5 text-blue-600">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">AI-powered voice protection</p>
                <p className="mt-1 text-sm text-slate-600">Continuous analysis for every protected call.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Protected Calls"
          value={String(metrics.protectedCalls)}
          detail={metrics.protectedCalls ? 'Completed protected calls' : 'No protected calls yet'}
          icon={Phone}
          tone="blue"
        />
        <MetricCard
          label="Threats Detected"
          value={String(metrics.threatsDetected)}
          detail={metrics.threatsDetected ? 'Unique risk indicators' : 'No threats detected'}
          icon={ShieldAlert}
          tone={metrics.threatsDetected ? 'red' : 'slate'}
        />
        <MetricCard
          label="Trusted Contacts"
          value={String(metrics.trustedContacts)}
          detail={metrics.trustedContacts ? 'Available for verification' : 'Add trusted contacts to enable speaker verification'}
          icon={Users}
          tone="green"
        />
        <MetricCard
          label="Total Call Time"
          value={formatDuration(metrics.totalSeconds)}
          detail={metrics.totalSeconds ? 'Across completed calls' : 'No completed calls yet'}
          icon={Clock3}
          tone="amber"
        />
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 lg:p-7">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-5 w-5 text-blue-600" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">How Saksham protects you</p>
            <h2 className="mt-1 text-xl font-bold text-slate-950">Saksham 2.0 Protection Pipeline</h2>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          {pipeline.map(([step, description], index) => (
            <div key={step} className="relative rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold tracking-[0.16em] text-blue-600">{step}</span>
                <span className="text-xs text-slate-400">0{index + 1}</span>
              </div>
              <p className="mt-3 text-sm font-medium leading-5 text-slate-800">{description}</p>
              {index < pipeline.length - 1 && (
                <ArrowRight className="absolute -right-3 top-1/2 z-10 hidden h-5 w-5 -translate-y-1/2 text-slate-300 lg:block" />
              )}
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <SectionHeading title="Recent Activity" subtitle="Your latest protected call history" />
          {metrics.endedCalls.length === 0 ? (
            <EmptyState icon={ShieldCheck} text="Your security activity will appear here after your first protected call." />
          ) : (
            <div className="mt-5 divide-y divide-slate-100">
              {metrics.endedCalls.slice(0, 5).map((call) => {
                const report = reportForCall(call, data?.reports ?? [])
                const duration = callDuration(call)
                const level = report?.final_risk_level

                return (
                  <div key={call.id} className="flex flex-wrap items-center justify-between gap-3 py-4 first:pt-0">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                        <Phone className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">Protected call</p>
                        <p className="mt-1 text-xs text-slate-500">{formatDate(call.ended_at ?? call.created_at)}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-slate-700">{duration == null ? 'Duration unavailable' : formatDuration(duration)}</p>
                      <p className={`mt-1 text-xs font-semibold ${riskClass(level)}`}>{level ?? 'Report unavailable'}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <SectionHeading title="Threat Overview" subtitle="Aggregated from available security reports" />
          {metrics.indicators.length === 0 ? (
            <EmptyState icon={ShieldAlert} text="No threats detected yet." />
          ) : (
            <div className="mt-5 flex flex-wrap gap-2">
              {metrics.indicators.map((indicator) => (
                <span key={indicator} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
                  {formatIndicator(indicator)}
                </span>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <SectionHeading title="Call Activity" subtitle="Based on completed call-session timestamps" />
          {metrics.endedCalls.length === 0 ? (
            <EmptyState icon={Clock3} text="Your call activity will appear here." />
          ) : (
            <div className="mt-5 space-y-3">
              {metrics.endedCalls.slice(0, 5).map((call) => (
                <div key={call.id} className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-blue-600" />
                  <div className="flex-1 border-b border-slate-100 pb-3">
                    <p className="text-sm text-slate-700">{formatDate(call.started_at ?? call.created_at)}</p>
                    <p className="mt-1 text-xs text-slate-500">{callDuration(call) == null ? 'Duration unavailable' : formatDuration(callDuration(call) ?? 0)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-amber-100 bg-amber-50 p-6">
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-5 w-5 text-amber-600" />
            <h2 className="text-lg font-bold text-slate-950">Security Tip</h2>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-700">
            Never share an OTP, password, or financial information because a caller creates urgency. End the call and verify the request through an independent trusted channel.
          </p>
        </section>
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone,
}: {
  label: string
  value: string
  detail: string
  icon: typeof Phone
  tone: 'blue' | 'green' | 'amber' | 'red' | 'slate'
}) {
  const tones = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-red-50 text-red-600',
    slate: 'bg-slate-100 text-slate-600',
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className={`rounded-lg p-2.5 ${tones[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <p className="text-3xl font-bold text-slate-950">{value}</p>
      </div>
      <p className="mt-5 text-sm font-semibold text-slate-800">{label}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  )
}

function SectionHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-xl font-bold text-slate-950">{title}</h2>
      <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
    </div>
  )
}

function EmptyState({
  icon: Icon,
  text,
}: {
  icon: typeof ShieldCheck
  text: string
}) {
  return (
    <div className="mt-5 flex min-h-28 items-center gap-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 text-sm text-slate-500">
      <Icon className="h-5 w-5 shrink-0 text-slate-400" />
      <span>{text}</span>
    </div>
  )
}

function formatIndicator(indicator: string) {
  return indicator
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function riskClass(level: CallSecurityReport['final_risk_level'] | undefined) {
  if (level === 'HIGH') return 'text-red-600'
  if (level === 'SUSPICIOUS') return 'text-amber-600'
  if (level === 'LOW') return 'text-green-600'
  return 'text-slate-400'
}
