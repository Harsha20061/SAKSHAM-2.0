export interface SignalingMessage {
  type:
    | 'call_offer'
    | 'call_answer'
    | 'ice_candidate'
    | 'call_end'
    | 'ping'
    | 'pong'
    | 'hello'
    | 'hello_ack'
    | 'error'

  session_id: string

  payload: Record<string, unknown>
}

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

export class SignalingSocket {
  private sessionId: string
  private token: string

  private onMessage: (
    message: SignalingMessage,
  ) => void

  private onOpen?: () => void
  private onClose?: () => void
  private onError?: (event: Event) => void

  private socket: WebSocket | null = null

  constructor(
    sessionId: string,
    token: string,
    onMessage: (
      message: SignalingMessage,
    ) => void,
    onOpen?: () => void,
    onClose?: () => void,
    onError?: (event: Event) => void,
  ) {
    this.sessionId = sessionId
    this.token = token
    this.onMessage = onMessage
    this.onOpen = onOpen
    this.onClose = onClose
    this.onError = onError
  }

  connect(): void {
    const wsUrl =
      `${WS_BASE_URL}/api/ws/${this.sessionId}` +
      `?token=${encodeURIComponent(this.token)}`

    this.socket = new WebSocket(wsUrl)

    this.socket.onopen = () => {
      console.log('WebSocket connected')

      this.send({
        type: 'hello',
        session_id: this.sessionId,
        payload: {},
      })

      this.onOpen?.()
    }

    this.socket.onmessage = (event) => {
      try {
        const message =
          JSON.parse(event.data) as SignalingMessage

        console.log('WS received:', message)

        this.onMessage(message)
      } catch (error) {
        console.error(
          'Invalid WebSocket message:',
          error,
        )
      }
    }

    this.socket.onerror = (event) => {
      console.error('WebSocket error:', event)

      this.onError?.(event)
    }

    this.socket.onclose = () => {
      console.log('WebSocket disconnected')

      this.onClose?.()
    }
  }

  send(message: SignalingMessage): void {
    if (
      !this.socket ||
      this.socket.readyState !== WebSocket.OPEN
    ) {
      console.warn(
        'WebSocket is not connected',
      )

      return
    }

    this.socket.send(
      JSON.stringify(message),
    )
  }

  close(): void {
    this.socket?.close()

    this.socket = null
  }

  isConnected(): boolean {
    return (
      this.socket?.readyState ===
      WebSocket.OPEN
    )
  }
}
