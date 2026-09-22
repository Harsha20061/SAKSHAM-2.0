import api from './api'

import type {
  Contact,
  CreateContactRequest,
  UpdateContactRequest,
  UserSearchResult,
  VoiceProfileMetadataResponse,
  VoiceProfileStatusResponse,
} from '../types/contacts'

export async function getContacts(
  trustedOnly = false,
): Promise<Contact[]> {
  const response = await api.get<Contact[]>(
    '/contacts',
    {
      params: {
        trusted_only: trustedOnly,
      },
    },
  )

  return response.data
}

export async function createContact(
  data: CreateContactRequest,
): Promise<Contact> {
  const response = await api.post<Contact>(
    '/contacts',
    data,
  )

  return response.data
}

export async function updateContact(
  contactId: string,
  data: UpdateContactRequest,
): Promise<Contact> {
  const response = await api.patch<Contact>(
    `/contacts/${contactId}`,
    data,
  )

  return response.data
}

export async function deleteContact(
  contactId: string,
): Promise<void> {
  await api.delete(`/contacts/${contactId}`)
}

export async function getVoiceProfile(
  contactId: string,
): Promise<VoiceProfileStatusResponse> {
  const response = await api.get<VoiceProfileStatusResponse>(
    `/contacts/${contactId}/voice-profile`,
  )

  return response.data
}

export async function createVoiceProfile(
  contactId: string,
  file: Blob,
  consent: boolean,
): Promise<VoiceProfileMetadataResponse> {
  const formData = new FormData()
  formData.append('file', file, 'voice-profile.wav')
  formData.append('consent', String(consent))

  const response = await api.post<VoiceProfileMetadataResponse>(
    `/contacts/${contactId}/voice-profile`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )

  return response.data
}

export async function updateVoiceProfile(
  contactId: string,
  file: Blob,
  consent: boolean,
): Promise<VoiceProfileMetadataResponse> {
  const formData = new FormData()
  formData.append('file', file, 'voice-profile.wav')
  formData.append('consent', String(consent))

  const response = await api.put<VoiceProfileMetadataResponse>(
    `/contacts/${contactId}/voice-profile`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )

  return response.data
}

export async function deleteVoiceProfile(
  contactId: string,
): Promise<void> {
  await api.delete(`/contacts/${contactId}/voice-profile`)
}

export async function searchUsers(
  query: string,
): Promise<UserSearchResult[]> {
  const response = await api.get<UserSearchResult[]>(
    '/auth/users/search',
    {
      params: {
        q: query,
      },
    },
  )

  return response.data
}