import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, MicOff, Phone, PhoneOff, Volume2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";

import { endCall, getCall, updateCallStatus } from "../services/calls";

import { SignalingSocket, type SignalingMessage } from "../services/websocket";

import { WebRTCService } from "../services/webrtc";

import { AnalysisSocket } from "../services/analysisWebSocket";

import type { AnalysisResult } from "../types/analysis";

import AnalysisPanel from "../components/call/AnalysisPanel";

/*
 * -----------------------------------------------------------
 * Call phases
 * -----------------------------------------------------------
 */

type CallPhase =
  | "LOADING"
  | "RINGING"
  | "CONNECTING"
  | "CONNECTED"
  | "ENDED"
  | "FAILED";

/*
 * -----------------------------------------------------------
 * Call page
 * -----------------------------------------------------------
 */

export default function Call() {
  const { callId } = useParams<{ callId: string }>();

  const navigate = useNavigate();

  /*
   * ---------------------------------------------------------
   * State
   * ---------------------------------------------------------
   */

  const [phase, setPhase] = useState<CallPhase>(
    callId ? "LOADING" : "FAILED",
  );

  const [isMuted, setIsMuted] = useState(false);

  const [error, setError] = useState<string | null>(
    callId ? null : "Invalid call ID.",
  );

  const [isCaller, setIsCaller] = useState(false);

  /*
   * Live analysis state
   */

  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null,
  );

  const [analysisConnected, setAnalysisConnected] = useState(false);

  /*
   * ---------------------------------------------------------
   * Refs
   * ---------------------------------------------------------
   */

  const localStreamRef = useRef<MediaStream | null>(null);

  const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
  const remoteStreamRef = useRef<MediaStream | null>(null);
  const webRTCRef = useRef<WebRTCService | null>(null);

  const signalingRef = useRef<SignalingSocket | null>(null);

  const analysisSocketRef = useRef<AnalysisSocket | null>(null);

  /*
   * ICE candidates can arrive before
   * remote SDP is available.
   */

  const remoteDescriptionSetRef = useRef(false);

  const pendingIceCandidatesRef = useRef<RTCIceCandidateInit[]>([]);

  /*
   * Prevent duplicate cleanup.
   */

  const cleanedUpRef = useRef(false);

  /*
   * Keep caller information in a ref as well.
   *
   * This prevents signaling callbacks from becoming
   * dependent on React state changes.
   */

  const isCallerRef = useRef(false);

  /*
   * ---------------------------------------------------------
   * Cleanup
   * ---------------------------------------------------------
   */

  const cleanup = useCallback(() => {
    if (cleanedUpRef.current) {
      return;
    }

    cleanedUpRef.current = true;

    console.log("[Call] Cleaning up call resources");

    /*
     * Stop analysis first.
     */

    try {
      analysisSocketRef.current?.stop();
    } catch (err) {
      console.warn("[Call] Failed to stop analysis:", err);
    }

    try {
      analysisSocketRef.current?.close();
    } catch (err) {
      console.warn("[Call] Failed to close analysis socket:", err);
    }

    analysisSocketRef.current = null;

    setAnalysisConnected(false);
    setAnalysisResult(null);

    /*
     * Stop microphone tracks.
     */

    localStreamRef.current?.getTracks().forEach((track) => {
      try {
        track.stop();
      } catch (err) {
        console.warn("[Call] Failed to stop media track:", err);
      }
    });

    localStreamRef.current = null;
    remoteStreamRef.current = null;

    /*
     * Close WebRTC.
     */

    try {
      webRTCRef.current?.close();
    } catch (err) {
      console.warn("[Call] Failed to close WebRTC:", err);
    }

    webRTCRef.current = null;

    /*
     * Close signaling.
     */

    try {
      signalingRef.current?.close();
    } catch (err) {
      console.warn("[Call] Failed to close signaling:", err);
    }

    signalingRef.current = null;

    /*
     * Reset ICE state.
     */

    pendingIceCandidatesRef.current = [];

    remoteDescriptionSetRef.current = false;
  }, []);

  /*
   * ---------------------------------------------------------
   * Microphone
   * ---------------------------------------------------------
   */

  const getLocalStream = useCallback(async (): Promise<MediaStream> => {
    /*
     * Reuse existing stream if available.
     */

    if (localStreamRef.current) {
      return localStreamRef.current;
    }

    const hasGetUserMedia =
      typeof navigator.mediaDevices?.getUserMedia === "function";

    console.log("[Call] Microphone capability:", {
      isSecureContext: window.isSecureContext,
      mediaDevices: navigator.mediaDevices,
      getUserMediaExists: hasGetUserMedia,
    });

    if (!hasGetUserMedia) {
      const message =
        "Microphone access requires a secure HTTPS connection on this mobile browser.";

      setError(message);
      throw new Error(message);
    }

    console.log("[Call] Requesting microphone access...");

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false,
    });

    localStreamRef.current = stream;

    return stream;
  }, []);

  /*
   * ---------------------------------------------------------
   * Flush queued ICE candidates
   * ---------------------------------------------------------
   */

  const flushPendingIceCandidates = useCallback(async () => {
    const webRTC = webRTCRef.current;

    if (!webRTC) {
      return;
    }

    if (!remoteDescriptionSetRef.current) {
      return;
    }

    const candidates = pendingIceCandidatesRef.current;

    /*
     * Clear queue before processing.
     */

    pendingIceCandidatesRef.current = [];

    for (const candidate of candidates) {
      try {
        await webRTC.addIceCandidate(candidate);
      } catch (err) {
        console.error("[Call] Failed to add queued ICE candidate:", err);
      }
    }
  }, []);

  /*
   * ---------------------------------------------------------
   * Connect analysis WebSocket
   * ---------------------------------------------------------
   */

  const connectAnalysis = useCallback(() => {
    if (!callId) {
      console.error("[Analysis] Call ID is missing");

      return;
    }

    const token = localStorage.getItem("echoguard_token");

    if (!token) {
      console.error("[Analysis] Authentication token missing");

      return;
    }

    /*
     * Prevent duplicate analysis sockets.
     */

    if (analysisSocketRef.current?.isConnected()) {
      console.log("[Analysis] Already connected");

      return;
    }

    /*
     * Close any stale socket before
     * creating a new one.
     */

    if (analysisSocketRef.current) {
      try {
        analysisSocketRef.current.close();
      } catch (err) {
        console.warn("[Analysis] Failed to close stale socket:", err);
      }

      analysisSocketRef.current = null;
    }

    console.log("[Analysis] Creating analysis WebSocket");

    const socket = new AnalysisSocket(
      callId,
      token,

      /*
       * Analysis result callback
       */

      (result) => {
        setAnalysisResult(result);
      },

      /*
       * Analysis socket connected
       */

      () => {
  console.log("[Analysis] WebSocket connected");

  setAnalysisConnected(true);

  // Start the current demo scenario.
  // This remains mock behavior until Abhinay's
  // real AI model is integrated.
  analysisSocketRef.current?.start("HIGH");

  // If the remote caller's stream already exists,
  // start sending it to the analysis WebSocket.
  if (remoteStreamRef.current) {
    void analysisSocketRef.current?.startAudioCapture(
      remoteStreamRef.current,
    );
  } else {
    console.log(
      "[Analysis] Waiting for remote audio stream...",
    );
  }
},
      /*
       * Analysis socket closed
       */

      () => {
        console.log("[Analysis] WebSocket closed");

        setAnalysisConnected(false);
      },
    );

    analysisSocketRef.current = socket;

    socket.connect();
  }, [callId]);

  /*
   * ---------------------------------------------------------
   * WebRTC initialization
   * ---------------------------------------------------------
   */

  const initializeWebRTC = useCallback(async () => {
    const stream = await getLocalStream();

    const webRTC = new WebRTCService({
      /*
       * ICE candidate generated locally.
       */

      onIceCandidate: (candidate) => {
        const socket = signalingRef.current;

        if (!socket) {
          return;
        }

        socket.send({
          type: "ice_candidate",
          session_id: callId ?? "",
          payload: {
            candidate: candidate.toJSON(),
          },
        });
      },

      /*
       * Remote audio received.
       */

      onTrack: (event) => {
  console.log("[WebRTC] Remote audio received");

  const remoteStream = event.streams[0];

  if (!remoteStream) {
    console.warn("[WebRTC] Remote stream missing");
    return;
  }

  // Store the caller's remote audio stream.
  remoteStreamRef.current = remoteStream;

  // Keep existing remote audio playback.
  if (remoteAudioRef.current) {
    remoteAudioRef.current.srcObject = remoteStream;

    remoteAudioRef.current.play().catch((err) => {
      console.warn(
        "[WebRTC] Browser blocked autoplay:",
        err,
      );
    });
  }

  // If the analysis WebSocket is already connected,
  // start analyzing the caller's audio.
  if (
    !isCallerRef.current &&
    analysisSocketRef.current?.isConnected()
  ) {
    void analysisSocketRef.current.startAudioCapture(
      remoteStream,
    );
  }
},

      /*
       * WebRTC connection state.
       */

      onConnectionStateChange: (connectionState) => {
        console.log("[WebRTC] Connection state:", connectionState);

        /*
         * Actual voice connection established.
         */

        if (connectionState === "connected") {
          setPhase("CONNECTED");

          /*
           * Only the receiver/protected user
           * should run Saksham 2.0 analysis.
           *
           * Caller:
           *   WebRTC connected → no analysis
           *
           * Receiver:
           *   WebRTC connected → start analysis
           */

          if (!isCallerRef.current) {
            connectAnalysis();
          }
        }

        /*
         * WebRTC failed.
         */

        if (
          connectionState === "failed" ||
          connectionState === "disconnected"
        ) {
          setPhase("FAILED");

          setError("WebRTC connection failed.");
        }
      },
    });

    webRTCRef.current = webRTC;

    /*
     * Add microphone tracks.
     */

    await webRTC.addLocalStream(stream);
  }, [callId, connectAnalysis, getLocalStream]);

  /*
   * ---------------------------------------------------------
   * Send WebRTC offer
   * ---------------------------------------------------------
   */

  const sendOffer = useCallback(async () => {
    const webRTC = webRTCRef.current;

    const socket = signalingRef.current;

    if (!webRTC || !socket) {
      console.error("[WebRTC] WebRTC or signaling unavailable");

      return;
    }

    try {
      setPhase("CONNECTING");

      console.log("[WebRTC] Creating offer...");

      const offer = await webRTC.createOffer();

      socket.send({
        type: "call_offer",
        session_id: callId ?? "",
        payload: {
          offer,
        },
      });

      console.log("[WebRTC] Offer sent");
    } catch (err) {
      console.error("[WebRTC] Failed to create offer:", err);

      setPhase("FAILED");

      setError("Failed to create call offer.");
    }
  }, [callId]);

  /*
   * ---------------------------------------------------------
   * Signaling message handler
   * ---------------------------------------------------------
   */

  const handleSignalingMessage = useCallback(
    async (message: SignalingMessage) => {
      const webRTC = webRTCRef.current;

      if (!webRTC) {
        console.warn("[Signaling] WebRTC not initialized");

        return;
      }

      console.log("[Signaling] Received:", message);

      try {
        switch (message.type) {
          /*
           * ------------------------------------------------
           * Signaling handshake
           * ------------------------------------------------
           */

          case "hello_ack": {
            console.log("[Signaling] Connection ready");

            /*
             * Only caller creates the offer.
             */

            if (isCallerRef.current) {
              await sendOffer();
            }

            break;
          }

          /*
           * ------------------------------------------------
           * Incoming WebRTC offer
           * ------------------------------------------------
           */

          case "call_offer": {
            console.log("[WebRTC] Received call offer");

            setPhase("CONNECTING");

            const offer = message.payload.offer as RTCSessionDescriptionInit;

            if (!offer) {
              throw new Error("Offer missing from call_offer");
            }

            /*
             * Set remote SDP.
             */

            await webRTC.setRemoteDescription(offer);

            remoteDescriptionSetRef.current = true;

            /*
             * Process queued ICE.
             */

            await flushPendingIceCandidates();

            /*
             * Create answer.
             */

            const answer = await webRTC.createAnswer();

            /*
             * Send answer.
             */

            signalingRef.current?.send({
              type: "call_answer",
              session_id: callId ?? "",
              payload: {
                answer,
              },
            });

            /*
             * Receiver accepts call.
             */

            try {
              await updateCallStatus(
                callId ?? "",
                "ACTIVE",
              );
            } catch (err) {
              console.warn(
                "[Call] Could not update receiver call to ACTIVE:",
                err,
              );
            }

            break;
          }

          /*
           * ------------------------------------------------
           * WebRTC answer
           * ------------------------------------------------
           */

          case "call_answer": {
            console.log("[WebRTC] Received call answer");

            const answer = message.payload.answer as RTCSessionDescriptionInit;

            if (!answer) {
              throw new Error("Answer missing from call_answer");
            }

            /*
             * Set remote SDP.
             */

            await webRTC.setRemoteDescription(answer);

            remoteDescriptionSetRef.current = true;

            /*
             * Process queued ICE.
             */

            await flushPendingIceCandidates();

            /*
             * Caller can mark call ACTIVE.
             */

            try {
              await updateCallStatus(
                callId ?? "",
                "ACTIVE",
              );
            } catch (err) {
              console.warn(
                "[Call] Could not update caller call to ACTIVE:",
                err,
              );
            }

            break;
          }

          /*
           * ------------------------------------------------
           * ICE candidate
           * ------------------------------------------------
           */

          case "ice_candidate": {
            const candidate = message.payload.candidate as RTCIceCandidateInit;

            if (!candidate) {
              console.warn("[ICE] Candidate missing");

              return;
            }

            /*
             * ICE can arrive before remote SDP.
             * Queue it until SDP exists.
             */

            if (!remoteDescriptionSetRef.current) {
              console.log("[ICE] Queueing candidate");

              pendingIceCandidatesRef.current.push(candidate);

              return;
            }

            try {
              await webRTC.addIceCandidate(candidate);
            } catch (err) {
              console.error("[ICE] Failed to add candidate:", err);
            }

            break;
          }

          /*
           * ------------------------------------------------
           * Remote party ended the call
           * ------------------------------------------------
           */

          case "call_end": {
            console.log("[Call] Remote party ended call");

            setPhase("ENDED");

            cleanup();

            navigate(
              isCallerRef.current
                ? "/dashboard"
                : `/call/${callId}/report`,
            );

            break;
          }

          /*
           * ------------------------------------------------
           * Server error
           * ------------------------------------------------
           */

          case "error": {
            console.error("[Signaling] Server error:", message.payload);

            break;
          }

          /*
           * ------------------------------------------------
           * Pong
           * ------------------------------------------------
           */

          case "pong":
            break;

          /*
           * ------------------------------------------------
           * Unknown message
           * ------------------------------------------------
           */

          default:
            console.log("[Signaling] Unhandled message:", message);
        }
      } catch (err) {
        console.error("[Signaling] Processing error:", err);

        setPhase("FAILED");

        setError("Failed to process call signaling.");
      }
    },
    [callId, cleanup, flushPendingIceCandidates, navigate, sendOffer],
  );

  /*
   * ---------------------------------------------------------
   * Connect signaling WebSocket
   * ---------------------------------------------------------
   */

  const connectSignaling = useCallback(async () => {
    const token = localStorage.getItem("echoguard_token");

    if (!token) {
      throw new Error("Authentication token not found.");
    }

    if (!callId) {
      throw new Error("Call ID is missing.");
    }

    /*
     * Prevent duplicate signaling sockets.
     */

    if (signalingRef.current) {
      try {
        signalingRef.current.close();
      } catch {
        // Ignore stale socket cleanup.
      }

      signalingRef.current = null;
    }

    const socket = new SignalingSocket(
      callId,
      token,
      handleSignalingMessage,

      /*
       * Connected
       */

      () => {
        console.log("[Signaling] WebSocket connected");

        setPhase(isCallerRef.current ? "CONNECTING" : "RINGING");
      },

      /*
       * Closed
       */

      () => {
        console.log("[Signaling] WebSocket closed");
      },

      /*
       * Error
       */

      () => {
        console.error("[Signaling] WebSocket error");
      },
    );

    signalingRef.current = socket;

    socket.connect();
  }, [callId, handleSignalingMessage]);

  /*
   * ---------------------------------------------------------
   * Initialize call
   * ---------------------------------------------------------
   */

  useEffect(() => {
    if (!callId) {
      return;
    }

    /*
     * A new call lifecycle begins.
     */

    cleanedUpRef.current = false;

    remoteDescriptionSetRef.current = false;

    pendingIceCandidatesRef.current = [];

    const sessionId = callId;

    let cancelled = false;

    async function initialize() {
      try {
        setPhase("LOADING");

        setError(null);

        /*
         * Get call session.
         */

        const currentCall = await getCall(sessionId);

        if (cancelled) {
          return;
        }

        /*
         * Get JWT.
         */

        const token = localStorage.getItem("echoguard_token");

        if (!token) {
          throw new Error("Authentication required.");
        }

        /*
         * Decode current user ID.
         */

        const currentUserId = getUserIdFromToken(token);

        if (!currentUserId) {
          throw new Error("Invalid authentication token.");
        }

        /*
         * Determine caller.
         */

        const caller = currentUserId === currentCall.caller_id;

        isCallerRef.current = caller;

        setIsCaller(caller);

        /*
         * Initialize WebRTC before
         * signaling starts.
         */

        await initializeWebRTC();

        if (cancelled) {
          return;
        }

        /*
         * Connect signaling.
         */

        await connectSignaling();
      } catch (err) {
        console.error("[Call] Initialization failed:", err);

        if (!cancelled) {
          setPhase("FAILED");

          setError(
            err instanceof Error ? err.message : "Failed to initialize call.",
          );
        }
      }
    }

    initialize();

    /*
     * Cleanup on unmount / call change.
     */

    return () => {
      cancelled = true;

      cleanup();
    };
  }, [callId, cleanup, connectSignaling, initializeWebRTC]);

  /*
   * ---------------------------------------------------------
   * Toggle mute
   * ---------------------------------------------------------
   */

  function toggleMute() {
    const stream = localStreamRef.current;

    if (!stream) {
      return;
    }

    const nextMuted = !isMuted;

    stream.getAudioTracks().forEach((track) => {
      track.enabled = !nextMuted;
    });

    setIsMuted(nextMuted);
  }

  /*
   * ---------------------------------------------------------
   * End call
   * ---------------------------------------------------------
   */

  async function handleEndCall() {
    if (!callId) {
      return;
    }

    try {
      /*
       * Notify remote party.
       */

      signalingRef.current?.send({
        type: "call_end",
        session_id: callId,
        payload: {},
      });

      /*
       * Update backend.
       */

      await endCall(callId);
    } catch (err) {
      console.error("[Call] Failed to end call:", err);
    } finally {
      setPhase("ENDED");

      cleanup();

      navigate(
        isCallerRef.current
          ? "/dashboard"
          : `/call/${callId}/report`,
      );
    }
  }

  /*
   * ---------------------------------------------------------
   * Status text
   * ---------------------------------------------------------
   */

  const statusText = getStatusText(phase, isCaller);

  /*
   * ---------------------------------------------------------
   * UI
   * ---------------------------------------------------------
   */

  return (
    <div className="flex min-h-[70vh] w-full justify-center">
      <div
        className={
          isCaller
            ? "flex w-full max-w-xl justify-center"
            : "grid w-full max-w-[1400px] gap-8 lg:grid-cols-[minmax(360px,0.8fr)_minmax(0,1.2fr)]"
        }
      >
        {/* =================================================
            CALL PANEL
            ================================================= */}

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-7 text-center shadow-2xl lg:p-9">
          {/* Call icon */}

          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-cyan-500/10">
            {phase === "CONNECTED" ? (
              <Volume2 className="h-8 w-8 text-cyan-400" />
            ) : (
              <Phone className="h-8 w-8 text-cyan-400" />
            )}
          </div>

          {/* Title */}

          <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
            Security operations
          </p>

          <h1 className="mt-2 text-2xl font-bold presentation-surface-text">
            Secure voice call
          </h1>

          <p className="mt-2 text-slate-400">{statusText}</p>

          {/* Error */}

          {error && (
            <div className="mt-5 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {/* Connection indicator */}

          {phase === "CONNECTED" && (
            <div className="mt-6 flex items-center justify-center gap-2 text-sm text-emerald-400">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              Voice connection active
            </div>
          )}

          {/* Call controls */}

          <div className="mt-10 flex justify-center gap-4">
            {/* Mute */}

            <button
              type="button"
              onClick={toggleMute}
              disabled={phase !== "CONNECTED"}
              className="flex h-12 w-12 items-center justify-center rounded-xl border border-slate-700 bg-slate-800 text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              title={isMuted ? "Unmute microphone" : "Mute microphone"}
            >
              {isMuted ? (
                <MicOff className="h-5 w-5" />
              ) : (
                <Mic className="h-5 w-5" />
              )}
            </button>

            {/* End call */}

            <button
              type="button"
              onClick={handleEndCall}
              className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-600 text-white transition hover:bg-red-500"
              title="End call"
            >
              <PhoneOff className="h-5 w-5" />
            </button>
          </div>

          {/* Remote audio */}

          <audio ref={remoteAudioRef} autoPlay playsInline className="hidden" />
        </div>

        {/* =================================================
            SAKSHAM 2.0 ANALYSIS PANEL
            ================================================= */}

        {!isCaller && (
          <AnalysisPanel
            result={analysisResult}
            connected={analysisConnected}
          />
        )}
      </div>
    </div>
  );
}

/*
 * -----------------------------------------------------------
 * JWT helper
 * -----------------------------------------------------------
 */

function getUserIdFromToken(token: string): string | null {
  try {
    const parts = token.split(".");

    if (parts.length !== 3) {
      return null;
    }

    /*
     * JWT uses URL-safe Base64.
     */

    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");

    /*
     * Add missing Base64 padding.
     */

    const paddedBase64 = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");

    const decoded = JSON.parse(atob(paddedBase64));

    if (typeof decoded.sub !== "string") {
      return null;
    }

    return decoded.sub;
  } catch {
    return null;
  }
}

/*
 * -----------------------------------------------------------
 * UI status helper
 * -----------------------------------------------------------
 */

function getStatusText(phase: CallPhase, caller: boolean): string {
  switch (phase) {
    case "LOADING":
      return "Preparing secure call...";

    case "RINGING":
      return caller ? "Calling..." : "Incoming call...";

    case "CONNECTING":
      return "Establishing secure connection...";

    case "CONNECTED":
      return "Connected • Voice channel secure";

    case "ENDED":
      return "Call ended";

    case "FAILED":
      return "Call connection failed";

    default:
      return "Preparing call...";
  }
}
