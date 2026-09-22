import asyncio
import base64
import hashlib
import io
import time
import uuid
import wave
from datetime import datetime, timezone

import numpy as np

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.db.models.call_session import CallSession
from app.db.models.contact import Contact
from app.db.models.speaker_profile import SpeakerProfile
from app.db.models.user import User
from app.db.models.risk_event import RiskLevel
from app.db.repositories.risk_event_repository import RiskEventRepository
from app.models.schemas import (
    AnalysisRequest,
    FinalAnalysisResult,
    RiskEvaluationRequest,
)
from app.services.ai_service import ai_service
from app.services.audio_buffer import RollingAudioBuffer
from app.services.audio_decoder import (
    decode_audio_to_pcm,
    pcm_duration_seconds,
)
from app.services.mock_analysis_service import (
    MockAnalysisService,
)
from app.services.risk_service import RiskService
from app.services.signaling_service import (
    SignalingService,
)

ASR_WINDOW_SECONDS = 5
ASR_HOP_SECONDS = 3

def pcm_to_wav_bytes(
    pcm_audio: np.ndarray,
    sample_rate: int = 16000,
) -> bytes:
    """
    Convert mono int16 PCM samples into a WAV byte stream.
    """

    pcm_audio = np.asarray(
        pcm_audio,
        dtype=np.int16,
    )

    if pcm_audio.size == 0:
        raise ValueError("PCM audio is empty.")

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # int16 = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(
            pcm_audio.tobytes()
        )

    return buffer.getvalue()
router = APIRouter()


# =========================================================
# HTTP ANALYSIS ENDPOINT
# =========================================================


@router.post(
    "/analysis",
    response_model=FinalAnalysisResult,
    response_model_exclude_none=True,
)
async def analyze_audio(
    request: AnalysisRequest,
):
    """
    Complete one-shot backend analysis pipeline.

    AI Service -> Risk Service -> Final Result

    This endpoint remains available even after
    real-time WebSocket analysis is added.
    """

    # -----------------------------------------------------
    # 1. AI Analysis
    # -----------------------------------------------------

    ai_result = await ai_service.analyze(
        request
    )

    # -----------------------------------------------------
    # 2. Convert to RiskEvaluationRequest
    # -----------------------------------------------------

    risk_request = RiskEvaluationRequest(
        spoof_probability=ai_result.spoof_probability,
        speaker_similarity=ai_result.speaker_similarity,
        scam_score=ai_result.scam_score,
    )

    # -----------------------------------------------------
    # 3. Risk Evaluation
    # -----------------------------------------------------

    risk_start = time.perf_counter()
    risk_result = RiskService.evaluate(
        risk_request
    )
    risk_latency_ms = int((time.perf_counter() - risk_start) * 1000)

    # -----------------------------------------------------
    # 4. Construct Final Result
    # -----------------------------------------------------

    return FinalAnalysisResult(
        session_id=ai_result.session_id,
        spoof_probability=ai_result.spoof_probability,
        speaker_similarity=ai_result.speaker_similarity,
        speaker_verification_status=ai_result.speaker_verification_status,
        scam_score=ai_result.scam_score,
        risk_score=risk_result.risk_score,
        risk_level=risk_result.risk_level,
        indicators=ai_result.indicators,
        latency_ms=float(ai_result.latency_ms),
    )


# =========================================================
# WEBSOCKET AUTHENTICATION
# =========================================================


async def authenticate_analysis_ws(
    token: str,
    db: AsyncSession,
):
    """
    Authenticate a WebSocket connection using the
    same JWT used by the normal REST API.
    """

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[
                settings.JWT_ALGORITHM
            ],
        )

        user_id_str = payload.get("sub")

        if not user_id_str:
            return None

        user_id = uuid.UUID(
            user_id_str
        )

    except (
        JWTError,
        ValueError,
    ):
        return None

    user_repo = UserRepository(db)

    return await user_repo.get_by_id(
        user_id
    )


# =========================================================
# REAL-TIME MOCK ANALYSIS LOOP
# =========================================================


async def run_mock_analysis(
    websocket: WebSocket,
    session_id: str,
    scenario: str,
    stop_event: asyncio.Event,
):
    """
    Continuously generate mock AI results and pass them
    through the existing mock Risk Engine.

    This is temporary.

    Later:

        MockAnalysisService -> Abhinay's AI model
        RiskService         -> Abdul's Risk Engine
    """

    while not stop_event.is_set():

        # -------------------------------------------------
        # 1. MOCK AI
        # -------------------------------------------------

        ai_result = (
            await MockAnalysisService.analyze(
                scenario=scenario
            )
        )

        # -------------------------------------------------
        # 2. MOCK RISK
        # -------------------------------------------------

        risk_request = RiskEvaluationRequest(
            spoof_probability=ai_result[
                "spoof_probability"
            ],
            speaker_similarity=ai_result[
                "speaker_similarity"
            ],
            scam_score=ai_result[
                "scam_score"
            ],
        )

        risk_result = RiskService.evaluate(
            risk_request
        )

        # -------------------------------------------------
        # 3. COMBINE AI + RISK RESULT
        # -------------------------------------------------

        analysis_result = {
            "session_id": session_id,

            "spoof_probability": ai_result[
                "spoof_probability"
            ],

            "speaker_similarity": ai_result[
                "speaker_similarity"
            ],

            "scam_score": ai_result[
                "scam_score"
            ],

            "risk_score": risk_result.risk_score,

            "risk_level": risk_result.risk_level,

            "indicators": ai_result[
                "indicators"
            ],

            "latency_ms": ai_result[
                "latency_ms"
            ],
        }

        # -------------------------------------------------
        # 4. SEND RESULT TO FRONTEND
        # -------------------------------------------------

        await websocket.send_json(
            {
                "type": "analysis_result",
                "session_id": session_id,
                "payload": analysis_result,
            }
        )

        # -------------------------------------------------
        # 5. WAIT 2 SECONDS
        # -------------------------------------------------

        # stop_event allows analysis_stop to terminate
        # the loop quickly.

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=2.0,
            )

        except asyncio.TimeoutError:
            pass


# =========================================================
# REAL-TIME ANALYSIS WEBSOCKET
# =========================================================



# =========================================================
# REAL-TIME AI ANALYSIS LOOP
# =========================================================


async def run_real_analysis(
    websocket: WebSocket,
    session_id: str,
    contact_id: str | None,
    stop_event: asyncio.Event,
    audio_ready_event: asyncio.Event,
    get_audio_window,
    active_profile=None,
    result_state: dict | None = None,
    db: AsyncSession | None = None,
):
    """
    Real-time AI analysis worker.

    Pipeline:

        PCM audio
            ↓
        5-second window
            ↓
        AIService
            ↓
        AASIST + ECAPA + ASR/Scam Detection
            ↓
        Current EchoGuard RiskService
            ↓
        analysis_result
            ↓
        React frontend

    Abdul's independent Risk Engine is intentionally NOT
    integrated yet.
    """

    SAMPLE_RATE = 16000
    WINDOW_SECONDS = ASR_WINDOW_SECONDS
    WINDOW_SAMPLES = SAMPLE_RATE * WINDOW_SECONDS

    print(
        "[Real Analysis] Worker started "
        f"session={session_id} "
        f"contact={contact_id}"
    )
    while not stop_event.is_set():

        # -------------------------------------------------
        # Wait until enough decoded audio is available
        # -------------------------------------------------

        try:
            await asyncio.wait_for(
                audio_ready_event.wait(),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            continue

        if stop_event.is_set():
            break

        # Clear the event for this analysis cycle.
        audio_ready_event.clear()

        # -------------------------------------------------
        # Get latest decoded PCM
        # -------------------------------------------------

        try:
            pcm_audio = get_audio_window()
        except Exception as exc:
            print(
                "[Real Analysis] "
                f"Failed to get PCM window: {exc}"
            )
            continue

        if pcm_audio is None:
            continue

        pcm_audio = np.asarray(
            pcm_audio,
            dtype=np.int16,
        )

        # -------------------------------------------------
        # Make sure we have at least 5 seconds
        # -------------------------------------------------

        if pcm_audio.size < WINDOW_SAMPLES:
            duration = pcm_audio.size / SAMPLE_RATE

            print(
                "[Real Analysis] "
                f"Waiting for audio: "
                f"{duration:.2f}s / "
                f"{WINDOW_SECONDS}s"
            )
            continue

        # -------------------------------------------------
        # Take latest 5 seconds
        # -------------------------------------------------

        pcm_window = pcm_audio[-WINDOW_SAMPLES:]

        print(
            "[Real Analysis] "
            f"Starting {WINDOW_SECONDS}s AI window "
            f"contact={contact_id}"
        )
        # -------------------------------------------------
        # Run blocking model inference outside event loop
        # -------------------------------------------------

        try:
            ai_result = await asyncio.to_thread(
                ai_service.analyze_pcm_sync,
                session_id,
                pcm_window,
                contact_id,
                SAMPLE_RATE,
                active_profile,
            )

        except Exception as exc:
            print(
                "[Real Analysis] "
                f"AI inference failed: {exc}"
            )

            try:
                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "payload": {
                            "code": "AI_ANALYSIS_FAILED",
                            "message": str(exc),
                        },
                    }
                )
            except Exception:
                pass

            continue

        # If shutdown was requested while inference was still running,
        # do not drop the final result we already computed. The worker
        # should stop only after the in-flight analysis result has been
        # flushed to the client.

        # -------------------------------------------------
        # Current EchoGuard Risk Engine
        # -------------------------------------------------

        try:
            risk_request = RiskEvaluationRequest(
                spoof_probability=(
                    ai_result.spoof_probability
                ),
                speaker_similarity=(
                    ai_result.speaker_similarity
                ),
                scam_score=(
                    ai_result.scam_score
                ),
            )

            risk_start = time.perf_counter()
            risk_result = RiskService.evaluate(
                risk_request
            )
            risk_latency_ms = int((time.perf_counter() - risk_start) * 1000)

        except Exception as exc:
            print(
                "[Real Analysis] "
                f"Risk evaluation failed: {exc}"
            )
            continue

        # -------------------------------------------------
        # Build final result for frontend
        # -------------------------------------------------

        if result_state is None:
            result_state = {"sequence": 0, "last_window_signature": None}

        window_signature = hashlib.sha256(
            np.asarray(pcm_window, dtype=np.int16).tobytes()
        ).hexdigest()

        if (
            result_state.get("last_window_signature") == window_signature
            and result_state.get("last_window_signature") is not None
        ):
            print(
                "[Real Analysis] Skipping duplicate window "
                f"signature={window_signature[:12]}"
            )
            continue

        result_state["last_window_signature"] = window_signature
        result_state["sequence"] = int(result_state.get("sequence", 0)) + 1

        speaker_verification_status = (
            ai_result.speaker_verification_status
            or (
                "VERIFIED"
                if ai_result.speaker_similarity is not None
                and ai_result.speaker_similarity >= 0.75
                else "MISMATCH"
                if ai_result.speaker_similarity is not None
                else "NOT_ENROLLED"
            )
        )

        pipeline = getattr(ai_result, "pipeline", None) or {}
        if hasattr(pipeline, "model_dump"):
            pipeline = pipeline.model_dump()
        elif not isinstance(pipeline, dict):
            pipeline = {}

        risk_pipeline = {
            "executed": True,
            "latency_ms": float(risk_latency_ms),
        }

        pipeline_payload = {
            "aasist": {
                "executed": bool((pipeline.get("aasist") or {}).get("executed", True)),
                "latency_ms": float((pipeline.get("aasist") or {}).get("latency_ms", getattr(ai_result, "aasist_latency_ms", 0) or 0) or 0),
            },
            "ecapa": {
                "executed": bool((pipeline.get("ecapa") or {}).get("executed", ai_result.speaker_similarity is not None)),
                "latency_ms": (
                    float((pipeline.get("ecapa") or {}).get("latency_ms", 0) or 0)
                    if bool((pipeline.get("ecapa") or {}).get("executed", ai_result.speaker_similarity is not None))
                    else None
                ),
            },
            "asr_scam": {
                "executed": bool((pipeline.get("asr_scam") or {}).get("executed", True)),
                "latency_ms": (
                    float((pipeline.get("asr_scam") or {}).get("latency_ms", getattr(ai_result, "asr_latency_ms", 0) or 0) or 0)
                    if bool((pipeline.get("asr_scam") or {}).get("executed", True))
                    else None
                ),
                "error": (pipeline.get("asr_scam") or {}).get("error"),
                "fallback": bool((pipeline.get("asr_scam") or {}).get("fallback", False)),
            },
            "risk_engine": risk_pipeline,
        }

        total_latency_ms = int(
            sum(
                stage["latency_ms"] or 0
                for stage in pipeline_payload.values()
            )
        )
        window_end = float(len(pcm_window) / 16000)
        window_start = max(0.0, window_end - 5.0)

        analysis_result = {
            "session_id": session_id,
            "spoof_probability": (
                ai_result.spoof_probability
            ),
            "speaker_similarity": (
                ai_result.speaker_similarity
            ),
            "speaker_verification_status": (
                speaker_verification_status
            ),
            "scam_score": (
                ai_result.scam_score
            ),
            "risk_score": (
                risk_result.risk_score
            ),
            "risk_level": (
                risk_result.risk_level
            ),
            "indicators": (
                ai_result.indicators
            ),
            "transcript": (
                ai_result.transcript
            ),
            "language": (
                ai_result.language
            ),
            "language_confidence": getattr(
                ai_result,
                "language_confidence",
                None,
            ),
            "latency_ms": float(total_latency_ms),
            "pipeline": pipeline_payload,
            "total_latency_ms": float(total_latency_ms),
            "window_start": window_start,
            "window_end": window_end,
            "sequence": result_state["sequence"],
        }
        asr_completed = bool(
            (pipeline_payload.get("asr_scam") or {}).get("executed")
        )
        if db is not None and asr_completed:
            risk_event = await RiskEventRepository(db).create(
                call_id=uuid.UUID(session_id),
                spoof_probability=float(ai_result.spoof_probability),
                speaker_similarity=ai_result.speaker_similarity,
                scam_score=float(ai_result.scam_score),
                risk_score=float(risk_result.risk_score),
                risk_level=RiskLevel(risk_result.risk_level),
                latency_ms=float(total_latency_ms),
                indicators=list(ai_result.indicators),
            )
            await db.commit()

        print(
            "[Telemetry Debug]\n"
            f"AASIST latency={pipeline_payload['aasist']['latency_ms']}\n"
            f"ECAPA latency={pipeline_payload['ecapa']['latency_ms']}\n"
            f"ASR latency={pipeline_payload['asr_scam']['latency_ms']}\n"
            f"Risk latency={pipeline_payload['risk_engine']['latency_ms']}\n"
            f"TOTAL latency={total_latency_ms}"
        )

        # -------------------------------------------------
        # Send result to React
        # -------------------------------------------------

        try:
            await websocket.send_json(
                {
                    "type": "analysis_result",
                    "session_id": session_id,
                    "sequence_number": result_state["sequence"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": analysis_result,
                }
            )
            print(
                "[Real Analysis] Result sent "
                f"risk={risk_result.risk_level} "
                f"score={risk_result.risk_score}"
            )

        except Exception as exc:
            print(
                "[Real Analysis] "
                f"Failed to send result: {exc}"
            )
            break

        if stop_event.is_set():
            break

        # -------------------------------------------------
        # Small cooldown
        # -------------------------------------------------

        if not stop_event.is_set():
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                pass

    print(
        "[Real Analysis] Worker stopped "
        f"session={session_id}"
    )

async def resolve_ai_contact_id(
    db: AsyncSession,
    session_id: str,
) -> str | None:
    """Resolve the best active contact ID for speaker verification."""

    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError as exc:
        raise ValueError("Invalid call session ID") from exc

    call_result = await db.execute(
        select(CallSession).where(
            CallSession.id == session_uuid
        )
    )

    call_session = call_result.scalar_one_or_none()

    if call_session is None:
        raise ValueError("Call session not found")

    candidate_user_ids = [call_session.caller_id, call_session.receiver_id]
    for user_id in candidate_user_ids:
        contact_result = await db.execute(
            select(Contact)
            .where(Contact.contact_user_id == user_id)
            .limit(1)
        )
        contact = contact_result.scalar_one_or_none()
        if contact is not None:
            print(
                "[Analysis WS] Speaker profile resolved: "
                f"contact={contact.id} user={user_id}"
            )
            return str(contact.id)

    return None

@router.websocket(
    "/analysis/ws/{session_id}"
)
async def analysis_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time EchoGuard analysis WebSocket.

    Flow:

        Frontend
            ↓
        analysis_start
            ↓
        Audio chunks
            ↓
        Audio decoder
            ↓
        PCM 16 kHz mono
            ↓
        Rolling audio buffer
            ↓
        Mock AI
            ↓
        Mock Risk
            ↓
        analysis_result
            ↓
        Frontend
    """

    # -----------------------------------------------------
    # 1. AUTHENTICATE USER
    # -----------------------------------------------------

    user = await authenticate_analysis_ws(
        token,
        db,
    )

    if not user:
        await websocket.close(
            code=1008,
            reason="Unauthorized",
        )
        return

    # -----------------------------------------------------
    # 2. VALIDATE SESSION ID
    # -----------------------------------------------------

    try:
        uuid.UUID(session_id)

    except ValueError:
        await websocket.close(
            code=1008,
            reason="Invalid session ID",
        )
        return

    # -----------------------------------------------------
    # 3. VALIDATE CALL PARTICIPANT
    # -----------------------------------------------------

    try:
        await SignalingService.validate_connection(
            db,
            session_id,
            user,
        )

    except ValueError as exc:
        await websocket.close(
            code=1008,
            reason=str(exc),
        )
        return

    # -----------------------------------------------------
    # 4. ACCEPT WEBSOCKET
    # -----------------------------------------------------

    await websocket.accept()

    print(
        f"[Analysis WS] Connected "
        f"session={session_id} "
        f"user={user.id}"
    )



    # -----------------------------------------------------
    # 5. INITIAL STATE
    # -----------------------------------------------------

    analysis_task = None
    stop_event = asyncio.Event()
    audio_ready_event = asyncio.Event()

    # Latest successfully decoded PCM stream.
    latest_pcm_audio = None
    last_ready_window_signature = None
    last_ready_duration_seconds = 0.0
    result_state = {"sequence": 0, "last_window_signature": None}

    # -----------------------------------------------------
    # COMPRESSED AUDIO BUFFER
    # -----------------------------------------------------

    audio_buffer = bytearray()

    # -----------------------------------------------------
    # MODEL-READY PCM BUFFER
    # -----------------------------------------------------

    pcm_buffer = RollingAudioBuffer(
        max_seconds=10
    )

    def get_latest_audio_window():
        """
        Return the bounded rolling PCM source.
        """
        return pcm_buffer.get_audio()

    # -----------------------------------------------------
    # AUDIO STATISTICS
    # -----------------------------------------------------

    total_audio_bytes = 0
    audio_chunk_count = 0

    # Safety limit for compressed audio.
    MAX_AUDIO_BUFFER_BYTES = (
        5 * 1024 * 1024
    )

    try:

        # -------------------------------------------------
        # SEND READY MESSAGE
        # -------------------------------------------------

        await websocket.send_json(
            {
                "type": "analysis_ready",
                "session_id": session_id,
                "payload": {
                    "message": (
                        "Audio analysis service ready"
                    )
                },
            }
        )

        # -------------------------------------------------
        # 6. WAIT FOR FRONTEND COMMANDS
        # -------------------------------------------------

        while True:

            message = (
                await websocket.receive_json()
            )

            message_type = message.get(
                "type"
            )

            # =============================================
            # AUDIO CHUNK
            # =============================================

            if message_type == "audio_chunk":

                payload = message.get(
                    "payload",
                    {},
                )

                audio_base64 = payload.get(
                    "audio_base64"
                )

                # -----------------------------------------
                # Validate audio payload
                # -----------------------------------------

                if not audio_base64:

                    await websocket.send_json(
                        {
                            "type": "error",
                            "session_id": session_id,
                            "payload": {
                                "code": (
                                    "MISSING_AUDIO"
                                ),
                                "message": (
                                    "audio_base64 "
                                    "is required"
                                ),
                            },
                        }
                    )

                    continue

                # -----------------------------------------
                # Decode Base64 audio
                # -----------------------------------------

                try:

                    audio_bytes = (
                        base64.b64decode(
                            audio_base64,
                            validate=True,
                        )
                    )

                except Exception:

                    await websocket.send_json(
                        {
                            "type": "error",
                            "session_id": session_id,
                            "payload": {
                                "code": (
                                    "INVALID_AUDIO"
                                ),
                                "message": (
                                    "Invalid base64 "
                                    "audio data"
                                ),
                            },
                        }
                    )

                    continue

                # -----------------------------------------
                # Ignore empty chunks
                # -----------------------------------------

                if not audio_bytes:
                    continue

                # -----------------------------------------
                # Protect backend memory
                # -----------------------------------------

                if (
                    len(audio_buffer)
                    + len(audio_bytes)
                    > MAX_AUDIO_BUFFER_BYTES
                ):

                    audio_buffer.clear()
                    pcm_buffer.clear()

                    total_audio_bytes = 0
                    audio_chunk_count = 0

                    await websocket.send_json(
                        {
                            "type": "error",
                            "session_id": session_id,
                            "payload": {
                                "code": (
                                    "AUDIO_BUFFER_LIMIT"
                                ),
                                "message": (
                                    "Audio buffer "
                                    "limit exceeded"
                                ),
                            },
                        }
                    )

                    continue

                # -----------------------------------------
                # Add audio to compressed buffer
                # -----------------------------------------

                audio_buffer.extend(
                    audio_bytes
                )

                total_audio_bytes += (
                    len(audio_bytes)
                )

                audio_chunk_count += 1

                # -----------------------------------------
                # Backend logging
                # -----------------------------------------

                print(
                    "[Analysis WS] "
                    f"Audio chunk "
                    f"#{audio_chunk_count} "
                    f"size={len(audio_bytes)} "
                    f"bytes "
                    f"buffer={len(audio_buffer)} "
                    f"bytes"
                )

                # -----------------------------------------
                # AUDIO DECODING
                # -----------------------------------------

                # Attempt decoding every 3 chunks.
                #
                # This avoids repeatedly attempting to
                # decode a very small/incomplete WebM stream.

                if (
                    audio_chunk_count >= 3
                    and audio_chunk_count % 3 == 0
                ):

                    compressed_audio = bytes(
                        audio_buffer
                    )

                    try:

                        pcm_audio = (
                            decode_audio_to_pcm(
                                compressed_audio
                            )
                        )

                        if pcm_audio is not None:

                            # The decoder returns the
                            # complete decoded stream
                            # currently available.
                            #
                            # Clear first to avoid
                            # duplicating previous PCM.

                            pcm_buffer.clear()

                            pcm_buffer.append(
                                pcm_audio
                            )

                            # The rolling PCM buffer is authoritative. The
                            # compressed container remains bounded by the
                            # existing safety limit because WebM fragments
                            # cannot be safely decoded independently.
                            latest_pcm_audio = pcm_buffer.get_audio()

                            duration = (
                                pcm_duration_seconds(
                                    pcm_audio
                                )
                            )

                            # The real AI worker requires a
                            # minimum 5-second model window.
                            if duration >= 5.0:
                                ready_window = pcm_buffer.get_latest_window(5)
                                ready_signature = hashlib.sha256(
                                    ready_window.tobytes()
                                ).hexdigest()
                                if (
                                    ready_signature != last_ready_window_signature
                                    and (
                                        last_ready_duration_seconds == 0.0
                                        or duration - last_ready_duration_seconds
                                        >= ASR_HOP_SECONDS
                                    )
                                ):
                                    last_ready_window_signature = ready_signature
                                    last_ready_duration_seconds = duration
                                    audio_ready_event.set()

                            print(
                                "[AudioDecoder] "
                                f"Decoded PCM "
                                f"samples="
                                f"{pcm_audio.size}"
                            )

                            print(
                                "[AudioDecoder] "
                                f"PCM duration="
                                f"{duration:.2f}s"
                            )

                            print(
                                "[AudioDecoder] "
                                "Sample rate="
                                "16000 Hz"
                            )

                            print(
                                "[AudioDecoder] "
                                "Channels=1"
                            )

                            print(
                                "[AudioDecoder] "
                                "Rolling buffer="
                                f"{pcm_buffer.duration_seconds():.2f}s"
                            )

                        else:

                            print(
                                "[AudioDecoder] "
                                "Audio stream "
                                "not decodable yet"
                            )

                    except Exception as exc:

                        print(
                            "[AudioDecoder] "
                            f"Decode error: {exc}"
                        )

                # -----------------------------------------
                # Acknowledge audio reception
                # -----------------------------------------

                await websocket.send_json(
                    {
                        "type": "audio_received",
                        "session_id": session_id,
                        "payload": {
                            "chunk_number": (
                                audio_chunk_count
                            ),
                            "chunk_size_bytes": (
                                len(audio_bytes)
                            ),
                            "total_audio_bytes": (
                                total_audio_bytes
                            ),
                            "buffer_size_bytes": (
                                len(audio_buffer)
                            ),
                            "pcm_buffer_seconds": (
                                round(
                                    pcm_buffer.duration_seconds(),
                                    2,
                                )
                            ),
                        },
                    }
                )

                # Audio chunks should not fall through
                # into the unknown-message handler.

                continue

            # =============================================
            # START ANALYSIS
            # =============================================

            if message_type == "analysis_start":

                payload = message.get(
                    "payload",
                    {},
                )

                scenario = str(
                    payload.get(
                        "scenario",
                        "LOW",
                    )
                ).upper()

                # Only allow our three controlled
                # hackathon demo scenarios.

                if scenario not in {
                    "LOW",
                    "SUSPICIOUS",
                    "HIGH",
                }:
                    scenario = "LOW"
                real_time = bool(
                    payload.get("real_time", False)
                )
                # -----------------------------------------
                # Stop existing analysis task
                # -----------------------------------------

                if analysis_task:

                    stop_event.set()

                    try:
                        await analysis_task

                    except Exception:
                        pass

                    analysis_task = None
                    stop_event.clear()

                # -----------------------------------------
                # Reset audio state
                # -----------------------------------------

                audio_buffer.clear()
                pcm_buffer.clear()

                total_audio_bytes = 0
                audio_chunk_count = 0

                latest_pcm_audio = None
                last_ready_window_signature = None
                last_ready_duration_seconds = 0.0
                audio_ready_event.clear()

                # -----------------------------------------
                # Create new analysis task
                # -----------------------------------------

                if real_time:
                    # -----------------------------------------
                    # REAL AI MODE
                    # -----------------------------------------

                    try:
                        ai_contact_id = await resolve_ai_contact_id(
                            db,
                            session_id,
                        )
                    except ValueError as exc:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "session_id": session_id,
                                "payload": {
                                    "code": "SPEAKER_PROFILE_NOT_FOUND",
                                    "message": str(exc),
                                },
                            }
                        )
                        continue

                    active_profile = None
                    if ai_contact_id is not None:
                        profile_result = await db.execute(
                            select(SpeakerProfile)
                            .where(
                                (SpeakerProfile.contact_id == uuid.UUID(ai_contact_id))
                                & (SpeakerProfile.status == "ACTIVE")
                            )
                            .order_by(SpeakerProfile.created_at.desc())
                        )
                        active_profile = profile_result.scalar_one_or_none()

                    analysis_task = asyncio.create_task(
                        run_real_analysis(
                            websocket=websocket,
                            session_id=session_id,
                            contact_id=ai_contact_id,
                            stop_event=stop_event,
                            audio_ready_event=audio_ready_event,
                            get_audio_window=get_latest_audio_window,
                            active_profile=active_profile,
                            result_state=result_state,
                            db=db,
                        )
                    )

                else:
                    # -----------------------------------------
                    # LEGACY / DEMO MOCK MODE
                    # -----------------------------------------

                    analysis_task = asyncio.create_task(
                        run_mock_analysis(
                            websocket=websocket,
                            session_id=session_id,
                            scenario=scenario,
                            stop_event=stop_event,
                        )
                    )

                await websocket.send_json(
                    {
                        "type": "analysis_started",
                        "session_id": session_id,
                        "payload": {
                            "scenario": scenario,
                        },
                    }
                )

                print(
                    f"[Analysis WS] Started "
                    f"scenario={scenario} "
                    f"session={session_id}"
                )

            # =============================================
            # STOP ANALYSIS
            # =============================================

            elif message_type == "analysis_stop":

                stop_event.set()

                if analysis_task:

                    try:
                        await analysis_task

                    except Exception:
                        pass

                    analysis_task = None

                stop_event.clear()

                # Clear buffered audio.

                audio_buffer.clear()
                pcm_buffer.clear()

                total_audio_bytes = 0
                audio_chunk_count = 0

                latest_pcm_audio = None
                last_ready_window_signature = None
                last_ready_duration_seconds = 0.0
                audio_ready_event.clear()

                await websocket.send_json(
                    {
                        "type": "analysis_stopped",
                        "session_id": session_id,
                        "payload": {},
                    }
                )

                print(
                    f"[Analysis WS] Stopped "
                    f"session={session_id}"
                )

            # =============================================
            # PING
            # =============================================

            elif message_type == "ping":

                await websocket.send_json(
                    {
                        "type": "pong",
                        "session_id": session_id,
                        "payload": {},
                    }
                )

            # =============================================
            # UNKNOWN MESSAGE
            # =============================================

            else:

                await websocket.send_json(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "payload": {
                            "code": (
                                "UNKNOWN_MESSAGE_TYPE"
                            ),
                            "message": (
                                "Unsupported analysis "
                                "message type"
                            ),
                        },
                    }
                )

    # -----------------------------------------------------
    # 7. CLIENT DISCONNECTED
    # -----------------------------------------------------

    except WebSocketDisconnect:

        stop_event.set()

        if analysis_task:

            try:
                await analysis_task

            except Exception:
                pass

        audio_buffer.clear()
        pcm_buffer.clear()
        latest_pcm_audio = None
        last_ready_duration_seconds = 0.0
        audio_ready_event.clear()

        print(
            f"[Analysis WS] Disconnected "
            f"session={session_id}"
        )

    # -----------------------------------------------------
    # 8. UNEXPECTED ERROR
    # -----------------------------------------------------

    except Exception as exc:

        stop_event.set()

        if analysis_task:

            try:
                await analysis_task

            except Exception:
                pass

        audio_buffer.clear()
        pcm_buffer.clear()
        latest_pcm_audio = None
        last_ready_duration_seconds = 0.0
        audio_ready_event.clear()

        print(
            f"[Analysis WS] Error "
            f"session={session_id}: {exc}"
        )

        try:

            await websocket.close(
                code=1011,
                reason="Analysis service error",
            )

        except Exception:
            pass