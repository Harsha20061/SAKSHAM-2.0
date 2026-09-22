export type VoiceProfileStatus =
  | 'ACTIVE'
  | 'NOT_ENROLLED'
  | 'PROCESSING'
  | 'FAILED'
  | 'REVOKED'

export interface VoiceProfileStatusResponse {
  enrolled: boolean
  status: VoiceProfileStatus
  created_at?: string | null
}

export interface VoiceProfileMetadataResponse {
  id: string
  contact_id: string
  status: 'ACTIVE' | 'REVOKED' | 'PROCESSING' | 'FAILED'
  model_name: string
  model_version: string
  sample_rate: number
  embedding_dimension: number
  created_at?: string | null
  updated_at?: string | null
  consent_timestamp?: string | null
  revoked_at?: string | null
}

export interface Contact {
  id: string
  contact_user_id: string
  nickname: string
  is_trusted: boolean
  created_at: string
}

export interface CreateContactRequest {
  contact_user_id: string
  nickname: string
  is_trusted: boolean
}

export interface UpdateContactRequest {
  nickname?: string
  is_trusted?: boolean
}

export interface UserSearchResult {
  id: string
  username: string
  display_name: string
}