export type RiskLevel =
  | 'LOW'
  | 'SUSPICIOUS'
  | 'HIGH'

export interface ModelStageTelemetry {
  executed: boolean
  latency_ms: number | null
  error?: string | null
  fallback?: boolean
}

export interface AnalysisPipeline {
  aasist: ModelStageTelemetry
  ecapa: ModelStageTelemetry
  asr_scam: ModelStageTelemetry
  risk_engine: ModelStageTelemetry
}

export interface AnalysisResult {
  session_id: string
  sequence_number?: number
  timestamp?: string

  spoof_probability: number
  speaker_similarity: number | null
  speaker_verification_status?: 'VERIFIED' | 'MISMATCH' | 'NOT_ENROLLED'
  scam_score: number
  transcript?: string
  language?: string | null
  language_confidence?: number | null

  risk_score: number
  risk_level: RiskLevel

  indicators: string[]

  latency_ms: number
  total_latency_ms?: number
  window_start?: number
  window_end?: number
  sequence?: number
  pipeline?: AnalysisPipeline
}