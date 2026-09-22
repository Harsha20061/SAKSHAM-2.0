import type { AnalysisPipeline, AnalysisResult, ModelStageTelemetry } from '../../types/analysis'
import AnalysisMetric from './AnalysisMetric'
import IndicatorList from './IndicatorList'
import RiskBadge from './RiskBadge'

interface AnalysisPanelProps {
  result: AnalysisResult | null
  connected: boolean
}

const stages: Array<{
  key: keyof AnalysisPipeline
  title: string
  description: string
}> = [
  {
    key: 'aasist',
    title: 'AASIST',
    description: 'Synthetic voice detection',
  },
  {
    key: 'ecapa',
    title: 'ECAPA',
    description: 'Trusted speaker verification',
  },
  {
    key: 'asr_scam',
    title: 'ASR + SCAM',
    description: 'Conversational threat analysis',
  },
  {
    key: 'risk_engine',
    title: 'RISK ENGINE',
    description: 'Combined risk assessment',
  },
]

function stageState(
  stage: ModelStageTelemetry | undefined,
  connected: boolean,
): string {
  if (stage?.executed) {
    return 'Completed'
  }

  return connected ? 'Waiting' : 'Standby'
}

function stageStateClass(stage: ModelStageTelemetry | undefined): string {
  if (stage?.executed) {
    return 'text-emerald-400'
  }

  return 'text-slate-500'
}

export default function AnalysisPanel({
  result,
  connected,
}: AnalysisPanelProps) {
  const pipeline = result?.pipeline
  const speakerPercent = result?.speaker_similarity == null
    ? null
    : Math.round(result.speaker_similarity * 100)
  const totalLatencyMs = result
    ? result.total_latency_ms ?? result.latency_ms
    : null
  const windowLabel = result?.sequence ?? '—'

  return (
    <section className="call-analysis-panel rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl lg:p-6">
      <header className="flex items-start justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
            Voice protection
          </p>
          <h2 className="mt-1 text-xl font-bold presentation-surface-text">
            Real-time voice protection
          </h2>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Continuous AI analysis of voice authenticity, speaker identity and conversational threats.
          </p>
        </div>

        <span className="flex shrink-0 items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          {connected ? 'Live protection' : 'Standby'}
        </span>
      </header>

      {!result ? (
        <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm font-semibold text-blue-900">
            {connected ? 'Analyzing incoming voice...' : 'Protection will begin when connected.'}
          </p>
          <p className="mt-1 text-sm text-blue-700">
            No risk values are shown until the backend returns the first completed analysis window.
          </p>
        </div>
      ) : (
        <>
          <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Overall risk
                </p>
                <p className="mt-2 text-4xl font-bold presentation-surface-text">
                  {Math.round(result.risk_score * 100)}%
                </p>
                <p className="mt-1 text-sm text-slate-500">Combined risk score</p>
              </div>
              <RiskBadge level={result.risk_level} />
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <AnalysisMetric label="Synthetic voice risk" value={result.spoof_probability} />
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-slate-400">Speaker verification</span>
                <span className="text-right text-sm font-semibold presentation-surface-text">
                  {result.speaker_verification_status ?? 'NOT ENROLLED'}
                </span>
              </div>
              <p className="mt-3 text-2xl font-bold presentation-surface-text">
                {speakerPercent == null ? 'Not enrolled' : `${speakerPercent}%`}
              </p>
              <p className="mt-1 text-xs text-slate-500">ECAPA similarity</p>
            </div>
            <AnalysisMetric label="Scam probability" value={result.scam_score} />
          </div>
        </>
      )}

      <div className="mt-6">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            AI protection pipeline
          </p>
          {result && (
            <span className="text-xs text-slate-500">
              Window #{windowLabel}
            </span>
          )}
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {stages.map((stage) => {
            const telemetry = pipeline?.[stage.key]

            return (
              <div
                key={stage.key}
                className="rounded-xl border border-slate-800 bg-slate-950/50 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold presentation-surface-text">{stage.title}</p>
                    <p className="mt-1 text-sm text-slate-500">{stage.description}</p>
                  </div>
                  <span className={`text-xs font-semibold ${stageStateClass(telemetry)}`}>
                    {telemetry?.executed ? '✓ ' : '● '}
                    {stageState(telemetry, connected)}
                  </span>
                </div>
                {telemetry?.latency_ms != null && (
                  <p className="mt-3 text-xs text-slate-500">
                    Completed · {Math.round(telemetry.latency_ms)} ms
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {result && (
        <>
          <div className="mt-6">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Detected threats
            </p>
            <IndicatorList indicators={result.indicators} />
          </div>

          <div className="mt-5 grid gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm sm:grid-cols-2">
            <div>
              <span className="text-slate-500">Transcript</span>
              <p className="mt-1 presentation-surface-text">
                {result.transcript ? `"${result.transcript}"` : 'No transcript returned'}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Language</span>
              <p className="mt-1 presentation-surface-text">
                {result.language ?? 'Not detected'}
                {result.language_confidence != null
                  ? ` · ${Math.round(result.language_confidence * 100)}% confidence`
                  : ''}
              </p>
            </div>
          </div>

          <p className="mt-4 text-right text-xs text-slate-500">
            Total analysis latency: {totalLatencyMs == null ? 'n/a' : `${Math.round(totalLatencyMs)} ms`}
          </p>
        </>
      )}
    </section>
  )
}
