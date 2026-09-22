import api from './api'

import type {
  CallResponse,
  CreateCallRequest,
  CallStatus,
  CallSecurityReport,
} from '../types/calls'

export async function createCall(
  data: CreateCallRequest,
): Promise<CallResponse> {
  const response = await api.post<CallResponse>(
    '/calls',
    data,
  )

  return response.data
}

export async function getCall(
  callId: string,
): Promise<CallResponse> {
  const response = await api.get<CallResponse>(
    `/calls/${callId}`,
  )

  return response.data
}

export async function updateCallStatus(
  callId: string,
  status: CallStatus,
): Promise<CallResponse> {
  const response = await api.patch<CallResponse>(
    `/calls/${callId}/status`,
    {
      status,
    },
  )

  return response.data
}

export async function endCall(
  callId: string,
): Promise<CallResponse> {
  const response = await api.post<CallResponse>(
    `/calls/${callId}/end`,
  )

  return response.data
}

export async function getCalls(
  status?: CallStatus,
): Promise<CallResponse[]> {
  const response = await api.get<CallResponse[]>(
    '/calls',
    {
      params: status ? { status } : undefined,
    },
  )

  return response.data
}

export async function getCallSecurityReport(
  callId: string,
): Promise<CallSecurityReport> {
  const response = await api.get<CallSecurityReport>(
    `/calls/${callId}/security-report`,
  )

  return response.data
}