import { useCallback, useEffect, useRef, useState } from 'react'
import { getCalls, endCall } from '../services/calls'
import type { CallResponse } from '../types/calls'

const POLL_INTERVAL = 2000

export function useIncomingCall() {
  const [incomingCall, setIncomingCall] =
    useState<CallResponse | null>(null)

  const handledCallIdsRef = useRef<Set<string>>(new Set())

  const checkIncomingCalls = useCallback(async () => {
    try {
      const calls = await getCalls('RINGING')

      const token = localStorage.getItem('echoguard_token')

      if (!token) {
        return
      }

      const currentUserId = getUserIdFromToken(token)

      if (!currentUserId) {
        return
      }

      const incoming = calls.find(
        (call) =>
          call.receiver_id === currentUserId &&
          !handledCallIdsRef.current.has(call.id),
      )

      if (incoming) {
        handledCallIdsRef.current.add(incoming.id)
        setIncomingCall(incoming)
      }
    } catch (error) {
      console.error(
        'Failed to check incoming calls:',
        error,
      )
    }
  }, [])

  useEffect(() => {
    checkIncomingCalls()

    const interval = window.setInterval(
      checkIncomingCalls,
      POLL_INTERVAL,
    )

    return () => {
      window.clearInterval(interval)
    }
  }, [checkIncomingCalls])

  const acceptCall = useCallback(() => {
    if (!incomingCall) {
      return null
    }

    const callId = incomingCall.id

    setIncomingCall(null)

    return callId
  }, [incomingCall])

  const rejectCall = useCallback(async () => {
    if (!incomingCall) {
      return
    }

    const callId = incomingCall.id

    setIncomingCall(null)

    try {
      await endCall(callId)
    } catch (error) {
      console.error(
        'Failed to reject incoming call:',
        error,
      )
    }
  }, [incomingCall])

  return {
    incomingCall,
    acceptCall,
    rejectCall,
  }
}

function getUserIdFromToken(
  token: string,
): string | null {
  try {
    const parts = token.split('.')

    if (parts.length !== 3) {
      return null
    }

    const base64 = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/')

    const decoded = JSON.parse(
      atob(base64),
    )

    if (
      typeof decoded.sub !== 'string'
    ) {
      return null
    }

    return decoded.sub
  } catch {
    return null
  }
}