export type CallStatus =
  | 'RINGING'
  | 'ACTIVE'
  | 'ENDED'
  | 'FAILED'

export interface CreateCallRequest {
  receiver_id: string
}

export interface CallResponse {
  id: string
  caller_id: string
  receiver_id: string
  status: CallStatus
  started_at: string | null
  ended_at: string | null
  created_at: string
}

export interface CallSecurityReport {
  call_id: string
  duration_seconds: number | null
  status: string
  started_at: string | null
  ended_at: string | null
  final_risk_score: number | null
  final_risk_level: CallRiskLevel | null
  peak_risk_score: number | null
  voice_authenticity_risk: number | null
  speaker_verification_status: string | null
  speaker_similarity: number | null
  scam_probability: number | null
  indicators: string[]
  recommended_action: string | null
}

export type CallRiskLevel = 'LOW' | 'SUSPICIOUS' | 'HIGH'