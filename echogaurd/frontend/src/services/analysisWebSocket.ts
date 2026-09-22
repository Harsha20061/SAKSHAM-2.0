import type { AnalysisResult } from '../types/analysis'

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'

export type AnalysisScenario =
  | 'LOW'
  | 'SUSPICIOUS'
  | 'HIGH'

export interface AnalysisMessage {
  type:
    | 'analysis_start'
    | 'analysis_result'
    | 'analysis_stop'
    | 'analysis_started'
    | 'analysis_stopped'
    | 'analysis_ready'
    | 'audio_chunk'
    | 'audio_received'
    | 'error'

  session_id: string
  sequence_number?: number
  timestamp?: string
  payload: Record<string, unknown>
}

export class AnalysisSocket {
  private sessionId: string
  private token: string

  private socket: WebSocket | null = null

  private onResult:
    | ((result: AnalysisResult) => void)
    | undefined

  private onOpen:
    | (() => void)
    | undefined

  private onClose:
    | (() => void)
    | undefined

  private mediaRecorder: MediaRecorder | null = null



  constructor(
    sessionId: string,
    token: string,
    onResult: (result: AnalysisResult) => void,
    onOpen?: () => void,
    onClose?: () => void,
  ) {
    this.sessionId = sessionId
    this.token = token
    this.onResult = onResult
    this.onOpen = onOpen
    this.onClose = onClose
  }

  connect(): void {
    const wsUrl =
      `${WS_BASE_URL}/api/analysis/ws/${this.sessionId}` +
      `?token=${encodeURIComponent(this.token)}`

    this.socket = new WebSocket(wsUrl)

    this.socket.onopen = () => {
      console.log('[Analysis WS] Connected')
      this.onOpen?.()
    }

    this.socket.onmessage = (event) => {
      try {
        const message =
          JSON.parse(event.data) as AnalysisMessage

        if (message.type === 'analysis_result') {
          const pipeline = message.payload.pipeline as
            | {
                aasist?: { latency_ms?: number | null }
                ecapa?: { latency_ms?: number | null }
                asr_scam?: { latency_ms?: number | null }
                risk_engine?: { latency_ms?: number | null }
              }
            | undefined

          console.log(
            '[Frontend Telemetry Debug]',
            `AASIST=${pipeline?.aasist?.latency_ms ?? null}`,
            `ECAPA=${pipeline?.ecapa?.latency_ms ?? null}`,
            `ASR=${pipeline?.asr_scam?.latency_ms ?? null}`,
            `Risk=${pipeline?.risk_engine?.latency_ms ?? null}`,
            `TOTAL=${message.payload.total_latency_ms ?? message.payload.latency_ms ?? null}`,
          )

          const result = {
            ...(message.payload as Record<string, unknown>),
            sequence_number: message.sequence_number,
            timestamp: message.timestamp,
          } as AnalysisResult

          this.onResult?.(result)
        }

        if (message.type === 'audio_received') {
          console.log(
            '[Analysis WS] Audio chunk received by backend:',
            message.payload,
          )
        }
      } catch (error) {
        console.error(
          '[Analysis WS] Invalid message:',
          error,
        )
      }
    }

    this.socket.onerror = (error) => {
      console.error(
        '[Analysis WS] Error:',
        error,
      )
    }

    this.socket.onclose = () => {
      console.log(
        '[Analysis WS] Disconnected',
      )

      this.stopAudioCapture()
      this.onClose?.()
    }
  }

  send(message: AnalysisMessage): void {
    if (
      !this.socket ||
      this.socket.readyState !== WebSocket.OPEN
    ) {
      console.warn(
        '[Analysis WS] Not connected',
      )

      return
    }

    this.socket.send(
      JSON.stringify(message),
    )
  }

  start(
  scenario: AnalysisScenario = 'LOW',
): void {
  this.send({
    type: 'analysis_start',
    session_id: this.sessionId,
    payload: {
      scenario,
      real_time: true,
    },
  })
}

  async startAudioCapture(
    stream: MediaStream,
  ): Promise<void> {
    if (!this.isConnected()) {
      console.warn(
        '[Analysis WS] Cannot capture audio before connection',
      )
      return
    }

    if (!stream.getAudioTracks().length) {
      console.warn(
        '[Analysis WS] No audio track available',
      )
      return
    }

    this.stopAudioCapture()



    const mimeType = this.getSupportedMimeType()

    if (!mimeType) {
      console.error(
        '[Analysis WS] No supported audio MIME type found',
      )
      return
    }

    this.mediaRecorder = new MediaRecorder(
      stream,
      {
        mimeType,
      },
    )

    this.mediaRecorder.ondataavailable = async (
      event,
    ) => {
      if (!event.data || event.data.size === 0) {
        return
      }

      try {
        const base64Audio =
          await this.blobToBase64(event.data)

        this.send({
          type: 'audio_chunk',
          session_id: this.sessionId,
          payload: {
            audio_base64: base64Audio,
            mime_type: mimeType,
            size_bytes: event.data.size,
            timestamp: new Date().toISOString(),
          },
        })

        console.log(
          `[Analysis WS] Sent audio chunk: ${event.data.size} bytes`,
        )
      } catch (error) {
        console.error(
          '[Analysis WS] Failed to encode audio chunk:',
          error,
        )
      }
    }

    this.mediaRecorder.onerror = (event) => {
      console.error(
        '[Analysis WS] MediaRecorder error:',
        event,
      )
    }

    this.mediaRecorder.start(1000)

    console.log(
      '[Analysis WS] Audio capture started',
      {
        mimeType,
        tracks: stream.getAudioTracks().length,
      },
    )
  }

  stopAudioCapture(): void {
    if (this.mediaRecorder) {
      if (
        this.mediaRecorder.state !== 'inactive'
      ) {
        this.mediaRecorder.stop()
      }

      this.mediaRecorder = null
    }



    console.log(
      '[Analysis WS] Audio capture stopped',
    )
  }

  stop(): void {
    this.stopAudioCapture()

    this.send({
      type: 'analysis_stop',
      session_id: this.sessionId,
      payload: {},
    })
  }

  close(): void {
    this.stopAudioCapture()

    this.socket?.close()
    this.socket = null
  }

  isConnected(): boolean {
    return (
      this.socket?.readyState ===
      WebSocket.OPEN
    )
  }

  private getSupportedMimeType():
    | string
    | null {
    const mimeTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
    ]

    for (const mimeType of mimeTypes) {
      if (
        MediaRecorder.isTypeSupported(
          mimeType,
        )
      ) {
        return mimeType
      }
    }

    return null
  }

  private async blobToBase64(
    blob: Blob,
  ): Promise<string> {
    const arrayBuffer =
      await blob.arrayBuffer()

    const bytes = new Uint8Array(
      arrayBuffer,
    )

    let binary = ''

    const chunkSize = 0x8000

    for (
      let i = 0;
      i < bytes.length;
      i += chunkSize
    ) {
      const chunk = bytes.subarray(
        i,
        i + chunkSize,
      )

      binary += String.fromCharCode(
        ...chunk,
      )
    }

    return btoa(binary)
  }
}