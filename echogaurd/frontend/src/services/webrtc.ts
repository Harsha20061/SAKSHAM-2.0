export interface WebRTCConfig {
  onIceCandidate?: (candidate: RTCIceCandidate) => void

  onTrack?: (event: RTCTrackEvent) => void

  onConnectionStateChange?: (
    state: RTCPeerConnectionState,
  ) => void
}

export class WebRTCService {
  private peerConnection: RTCPeerConnection

  constructor(config: WebRTCConfig = {}) {
    this.peerConnection = new RTCPeerConnection({
      iceServers: [
        {
          urls: 'stun:stun.l.google.com:19302',
        },
      ],
    })

    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate && config.onIceCandidate) {
        config.onIceCandidate(event.candidate)
      }
    }

    this.peerConnection.ontrack = (event) => {
      if (config.onTrack) {
        config.onTrack(event)
      }
    }

    this.peerConnection.onconnectionstatechange = () => {
      if (config.onConnectionStateChange) {
        config.onConnectionStateChange(
          this.peerConnection.connectionState,
        )
      }
    }
  }

  async addLocalStream(
    stream: MediaStream,
  ): Promise<void> {
    for (const track of stream.getTracks()) {
      this.peerConnection.addTrack(track, stream)
    }
  }

  async createOffer(): Promise<RTCSessionDescriptionInit> {
    const offer =
      await this.peerConnection.createOffer()

    await this.peerConnection.setLocalDescription(
      offer,
    )

    return offer
  }

  async createAnswer(): Promise<RTCSessionDescriptionInit> {
    const answer =
      await this.peerConnection.createAnswer()

    await this.peerConnection.setLocalDescription(
      answer,
    )

    return answer
  }

  async setRemoteDescription(
    description: RTCSessionDescriptionInit,
  ): Promise<void> {
    await this.peerConnection.setRemoteDescription(
      new RTCSessionDescription(description),
    )
  }

  async addIceCandidate(
    candidate: RTCIceCandidateInit,
  ): Promise<void> {
    await this.peerConnection.addIceCandidate(
      new RTCIceCandidate(candidate),
    )
  }

    getRemoteStream(): MediaStream | null {
    const receivers =
      this.peerConnection.getReceivers()

    const audioTracks =
      receivers
        .filter(
          (receiver) =>
            receiver.track &&
            receiver.track.kind === 'audio',
        )
        .map(
          (receiver) =>
            receiver.track,
        )

    if (audioTracks.length === 0) {
      return null
    }

    return new MediaStream(audioTracks)
  }

  getConnectionState(): RTCPeerConnectionState {
    return this.peerConnection.connectionState
  }


  close(): void {
    this.peerConnection.close()
  }
}