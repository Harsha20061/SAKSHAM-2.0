import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getCallSecurityReport } from '../services/calls'
import type { CallSecurityReport as Report } from '../types/calls'

const riskCopy = {
  LOW: 'No significant impersonation or social-engineering indicators were detected.',
  SUSPICIOUS: 'This call contains signals that should be independently verified.',
  HIGH: 'This call shows strong signs of possible voice impersonation or social engineering.',
}

const indicatorLabels: Record<string, string> = {
  otp_request: 'OTP REQUESTED',
  urgency: 'URGENCY',
  authority_impersonation: 'AUTHORITY IMPERSONATION',
  secrecy_pressure: 'SECRECY PRESSURE',
  money_request: 'MONEY REQUEST',
}

const highSeverityIndicators = new Set([
  'otp_request',
  'money_request',
  'authority_impersonation',
])

export default function CallSecurityReport() {
  const { callId } = useParams<{ callId: string }>()
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!callId) return

    getCallSecurityReport(callId)
      .then(setReport)
      .catch(() => setError('Unable to load the call security report.'))
  }, [callId])

  if (error) {
    return <p className="text-sm text-red-400">{error}</p>
  }

  if (!report) {
    return <p className="text-sm text-slate-400">Loading security report...</p>
  }

  const riskLevel = report.final_risk_level
  const riskStyle = riskLevelStyles(riskLevel)
  const percent = (value: number | null) =>
    value == null ? 'n/a' : `${Math.round(value * 100)}%`

  return (
    <div className="mx-auto max-w-4xl">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl sm:p-8">
        <p className="text-sm font-medium tracking-wider text-cyan-400">CALL SECURITY REPORT</p>

        <div className={`mt-5 rounded-2xl border p-6 ${riskStyle.container}`}>
          <p className="text-xs uppercase tracking-wider opacity-80">Final risk status</p>
          <h1 className={`mt-2 text-4xl font-bold ${riskStyle.text}`}>
            {riskLevel ?? 'UNAVAILABLE'}
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-slate-200">
            {riskLevel ? riskCopy[riskLevel] : 'No completed risk assessment is available for this call.'}
          </p>
          <p className="mt-5 text-sm text-slate-300">
            Overall Risk Score
            <span className="ml-3 text-3xl font-bold text-white">
              {percent(report.final_risk_score)}
            </span>
          </p>
        </div>

        <section className="mt-8">
          <SectionTitle>Security signals</SectionTitle>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <SignalCard
              label="Synthetic Voice Probability"
              value={percent(report.voice_authenticity_risk)}
              tone={metricTone(report.voice_authenticity_risk)}
            />
            <SignalCard
              label="Speaker Verification"
              value={report.speaker_verification_status ?? 'n/a'}
              tone={speakerTone(report.speaker_verification_status)}
            />
            <SignalCard
              label="Speaker Similarity"
              value={percent(report.speaker_similarity)}
              tone="neutral"
            />
            <SignalCard
              label="Scam Probability"
              value={percent(report.scam_probability)}
              tone={metricTone(report.scam_probability)}
            />
          </div>
        </section>

        <section className="mt-8">
          <SectionTitle>Detected threats</SectionTitle>
          {report.indicators.length === 0 ? (
            <p className="text-sm text-slate-400">
              No suspicious conversational indicators detected.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {report.indicators.map((indicator) => (
                <span
                  key={indicator}
                  className={`rounded-lg border px-3 py-2 text-xs font-semibold ${
                    highSeverityIndicators.has(indicator)
                      ? 'border-red-500/40 bg-red-500/10 text-red-300'
                      : 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                  }`}
                >
                  {indicatorLabels[indicator] ?? formatIndicator(indicator)}
                </span>
              ))}
            </div>
          )}
        </section>

        {report.recommended_action && (
          <section className={`mt-8 rounded-xl border p-5 ${riskStyle.container}`}>
            <SectionTitle>Recommended action</SectionTitle>
            <p className="mt-2 text-sm text-slate-100">{report.recommended_action}</p>
          </section>
        )}

        <section className="mt-8 border-t border-slate-800 pt-6">
          <SectionTitle>Call details</SectionTitle>
          <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
            <ReportValue label="Call ID" value={report.call_id} />
            <ReportValue
              label="Duration"
              value={report.duration_seconds == null ? 'n/a' : formatDuration(report.duration_seconds)}
            />
            <ReportValue label="Status" value={report.status} />
          </div>
          <p className="mt-4 text-sm text-slate-400">
            Peak Risk Score: <span className="text-white">{percent(report.peak_risk_score)}</span>
          </p>
        </section>

        <Link
          to="/dashboard"
          className="mt-7 inline-block rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}

function SectionTitle({ children }: { children: string }) {
  return <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{children}</h2>
}

function SignalCard({ label, value, tone }: { label: string; value: string; tone: Tone }) {
  return (
    <div className={`rounded-xl border p-4 ${toneStyles[tone]}`}>
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white">{value}</p>
    </div>
  )
}

function ReportValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-all text-slate-200">{value}</p>
    </div>
  )
}

type Tone = 'green' | 'amber' | 'red' | 'neutral'

const toneStyles: Record<Tone, string> = {
  green: 'border-emerald-500/30 bg-emerald-500/10',
  amber: 'border-amber-500/30 bg-amber-500/10',
  red: 'border-red-500/30 bg-red-500/10',
  neutral: 'border-slate-700 bg-slate-950/60',
}

function riskLevelStyles(level: Report['final_risk_level']) {
  if (level === 'HIGH') return { container: 'border-red-500/40 bg-red-500/10', text: 'text-red-300' }
  if (level === 'SUSPICIOUS') return { container: 'border-amber-500/40 bg-amber-500/10', text: 'text-amber-300' }
  return { container: 'border-emerald-500/40 bg-emerald-500/10', text: 'text-emerald-300' }
}

function metricTone(value: number | null): Tone {
  if (value == null || value < 0.4) return 'green'
  if (value < 0.7) return 'amber'
  return 'red'
}

function speakerTone(status: string | null): Tone {
  if (status === 'VERIFIED') return 'green'
  if (status === 'MISMATCH') return 'red'
  return 'amber'
}

function formatIndicator(indicator: string) {
  return indicator.replace(/_/g, ' ').toUpperCase()
}

function formatDuration(seconds: number) {
  const rounded = Math.max(0, Math.round(seconds))
  const minutes = Math.floor(rounded / 60)
  const remainingSeconds = rounded % 60
  return minutes ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
}
