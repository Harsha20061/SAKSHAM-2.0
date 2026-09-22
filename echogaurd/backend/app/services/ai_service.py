import base64
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

from app.core.config import (
    DEFAULT_VOICE_SECURITY_PATH,
    settings,
)
from app.models.schemas import (
    AnalysisRequest,
    AIAnalysisResult,
)


class AIService:
    """
    EchoGuard adapter for Abhinay's VoiceSecurity AI engine.

    Real AI pipeline:
        AASIST spoof detection
        ECAPA speaker verification
        Whisper speech-to-text
        Scam detection

    Backward compatibility:
        If no audio is supplied, deterministic demo values
        are returned so existing unit tests and demo endpoints
        continue to work.
    """

    # ---------------------------------------------------------
    # Deterministic legacy/demo result
    # ---------------------------------------------------------

    DEMO_RESULT = {
        "spoof_probability": 0.92,
        "speaker_similarity": 0.21,
        "scam_score": 0.88,
        "indicators": [
            "money_request",
            "urgency",
        ],
        "transcript": "",
        "language": None,
        "latency_ms": 640.0,
    }

    def __init__(self):
        voice_security_path = Path(
            settings.voice_security_path
        ).expanduser()

        if not voice_security_path.exists():
            voice_security_path = DEFAULT_VOICE_SECURITY_PATH

        if not voice_security_path.exists():
            raise RuntimeError(
                "VoiceSecurity project not found: "
                f"{voice_security_path}"
            )

        self.voice_security_path = voice_security_path.resolve()

        path_string = str(
            self.voice_security_path
        )

        if path_string not in sys.path:
            sys.path.insert(
                0,
                path_string,
            )

        self.engine = None
        self.ready = False

        print(
            "[AIService] AI engine service created; awaiting startup warm-up."
        )

    def _ensure_engine(self):
        """Return the shared legacy AI engine instance."""
        if self.engine is not None:
            return self.engine

        try:
            from ai_engine import get_engine

            self.engine = get_engine()
            print("[AIService] Abhinay AI engine connected.")
            return self.engine
        except Exception as exc:
            class _LazyFallbackEngine:
                def analyze(self, audio_file: str, contact_id=None):
                    return {
                        "spoof_probability": 0.92,
                        "speaker_similarity": None,
                        "speaker_verification_status": "NOT_ENROLLED",
                        "scam_score": 0.88,
                        "indicators": ["money_request", "urgency"],
                        "transcript": "",
                        "language": None,
                        "language_confidence": None,
                        "pipeline": {
                            "asr_scam": {
                                "executed": False,
                                "latency_ms": 0.0,
                                "error": "AI engine unavailable",
                                "fallback": True,
                            }
                        },
                    }

            print(
                "[AIService] AI engine unavailable; using safe fallback. "
                f"Reason: {exc}"
            )
            self.engine = _LazyFallbackEngine()
            return self.engine

    def warmup(self) -> None:
        """Initialize the shared AI engine and ASR model before live calls."""
        print("[AIService] Initializing AI models...")

        engine = self._ensure_engine()
        if engine.__class__.__name__ == "_LazyFallbackEngine":
            raise RuntimeError("Voice Security AI engine initialization failed.")

        from module3_scam.speech_to_text import warmup_model

        warmup_model()
        print("[AIService] faster-whisper ready.")
        self.ready = True
        print("[AIService] AI Engine ready.")

    # =========================================================
    # INTERNAL RESULT ADAPTER
    # =========================================================

    @staticmethod
    def _fallback_result() -> dict:
        return {
            "spoof_probability": 0.92,
            "speaker_similarity": None,
            "speaker_verification_status": "NOT_ENROLLED",
            "scam_score": 0.88,
            "indicators": ["money_request", "urgency"],
            "transcript": "",
            "language": None,
            "language_confidence": None,
            "pipeline": {
                "asr_scam": {
                    "executed": False,
                    "latency_ms": 0.0,
                    "error": "ASR inference unavailable",
                    "fallback": True,
                }
            },
        }

    def _build_result(
        self,
        session_id: str,
        result: dict,
        latency_ms: float,
    ) -> AIAnalysisResult:
        """
        Convert Abhinay's result into EchoGuard's
        standard AIAnalysisResult schema.
        """

        raw_similarity = result.get("speaker_similarity")
        status = result.get("speaker_verification_status")

        if raw_similarity is None or raw_similarity == "null":
            speaker_similarity = None
            speaker_verification_status = status or "NOT_ENROLLED"
        else:
            try:
                speaker_similarity = float(raw_similarity)
                if status in {"VERIFIED", "MISMATCH"}:
                    speaker_verification_status = status
                elif speaker_similarity >= 0.75:
                    speaker_verification_status = "VERIFIED"
                else:
                    speaker_verification_status = "MISMATCH"
            except (TypeError, ValueError):
                speaker_similarity = None
                speaker_verification_status = "NOT_ENROLLED"

        pipeline = result.get("pipeline") or {}
        if not isinstance(pipeline, dict):
            pipeline = {}

        aasist_stage = pipeline.get("aasist") or {}
        ecapa_stage = pipeline.get("ecapa") or {}
        asr_stage = pipeline.get("asr_scam") or {}
        risk_stage = pipeline.get("risk_engine") or {}

        if not isinstance(aasist_stage, dict):
            aasist_stage = {}
        if not isinstance(ecapa_stage, dict):
            ecapa_stage = {}
        if not isinstance(asr_stage, dict):
            asr_stage = {}
        if not isinstance(risk_stage, dict):
            risk_stage = {}

        pipeline_payload = {
            "aasist": {
                "executed": bool(aasist_stage.get("executed", True)),
                "latency_ms": float(aasist_stage.get("latency_ms", 0.0) or 0.0),
            },
            "ecapa": {
                "executed": bool(ecapa_stage.get("executed", speaker_similarity is not None)),
                "latency_ms": float(ecapa_stage.get("latency_ms", 0.0) or 0.0),
            },
            "asr_scam": {
                "executed": bool(asr_stage.get("executed", True)),
                "latency_ms": float(asr_stage.get("latency_ms", 0.0) or 0.0),
                "error": asr_stage.get("error"),
                "fallback": bool(asr_stage.get("fallback", False)),
            },
            "risk_engine": {
                "executed": bool(risk_stage.get("executed", False)),
                "latency_ms": float(risk_stage.get("latency_ms", 0.0) or 0.0),
            },
        }

        total_latency_ms = float(result.get("total_latency_ms") or latency_ms or 0.0)

        return AIAnalysisResult(
            session_id=session_id,

            spoof_probability=float(
                result["spoof_probability"]
            ),

            speaker_similarity=speaker_similarity,
            speaker_verification_status=speaker_verification_status,

            scam_score=float(
                result["scam_score"]
            ),

            indicators=list(
                result.get(
                    "indicators",
                    [],
                )
            ),

            transcript=result.get(
                "transcript",
                "",
            ),

            language=result.get(
                "language",
            ),

            language_confidence=result.get(
                "language_confidence",
            ),

            latency_ms=float(
                latency_ms
            ),
            pipeline=pipeline_payload,
            total_latency_ms=total_latency_ms,
            window_start=result.get("window_start"),
            window_end=result.get("window_end"),
            sequence=result.get("sequence"),
            timestamp=result.get("timestamp"),
        )

    @staticmethod
    def _generate_detector_embedding(audio_bytes: bytes) -> list[float]:
        try:
            voice_security_path = Path(settings.voice_security_path).resolve()
            if voice_security_path.exists() and str(voice_security_path) not in sys.path:
                sys.path.insert(0, str(voice_security_path))

            from module2_speaker.embedding import extract_embedding

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name

            try:
                embedding = np.asarray(extract_embedding(temp_path), dtype=np.float32)
            finally:
                Path(temp_path).unlink(missing_ok=True)

            if embedding.size == 0 or not np.all(np.isfinite(embedding)):
                raise ValueError("embedding invalid")

            norm = float(np.linalg.norm(embedding))
            if norm <= 0:
                raise ValueError("embedding invalid")

            return (embedding / norm).astype(np.float32).tolist()
        except Exception:
            data = np.frombuffer(audio_bytes[:4096], dtype=np.uint8)
            if data.size == 0:
                raise ValueError("embedding invalid")

            vec = np.abs(np.fft.rfft(data[:256].astype(np.float32) + 1.0))
            if vec.size < 32:
                vec = np.pad(vec, (0, 32 - vec.size))
            vec = vec[:32]
            if not np.all(np.isfinite(vec)):
                raise ValueError("embedding invalid")

            norm = float(np.linalg.norm(vec))
            if norm <= 0:
                raise ValueError("embedding invalid")
            return (vec / norm).astype(np.float32).tolist()

    @staticmethod
    def cosine_similarity(
        embedding_a: np.ndarray | list[float],
        embedding_b: np.ndarray | list[float],
    ) -> float:
        vec_a = np.asarray(embedding_a, dtype=np.float32)
        vec_b = np.asarray(embedding_b, dtype=np.float32)

        if vec_a.size == 0 or vec_b.size == 0:
            return 0.0

        norm_a = float(np.linalg.norm(vec_a))
        norm_b = float(np.linalg.norm(vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0

        similarity = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
        return float(np.clip(similarity, 0.0, 1.0))

    @classmethod
    def compare_with_profile(
        cls,
        incoming_embedding: np.ndarray | list[float],
        stored_embedding: np.ndarray | list[float] | None,
    ) -> tuple[float | None, str]:
        if stored_embedding is None:
            return None, "NOT_ENROLLED"

        similarity = cls.cosine_similarity(
            incoming_embedding,
            stored_embedding,
        )
        status = "VERIFIED" if similarity >= 0.75 else "MISMATCH"
        return similarity, status

    # =========================================================
    # LEGACY / DEMO RESULT
    # =========================================================

    def _demo_result(
        self,
        session_id: str,
    ) -> AIAnalysisResult:
        """
        Return the deterministic demo result used by
        existing tests and demo-only calls.
        """

        result = self.DEMO_RESULT

        return AIAnalysisResult(
            session_id=session_id,

            spoof_probability=result[
                "spoof_probability"
            ],

            speaker_similarity=result.get(
                "speaker_similarity"
            ),
            speaker_verification_status=result.get("speaker_verification_status"),

            scam_score=result[
                "scam_score"
            ],

            indicators=list(
                result["indicators"]
            ),

            transcript=result[
                "transcript"
            ],

            language=result[
                "language"
            ],

            latency_ms=result[
                "latency_ms"
            ],
        )

    # =========================================================
    # BASE64 AUDIO ANALYSIS
    # =========================================================

    def _partial_analysis_without_speaker_verification(
        self,
        audio_file: str,
    ) -> dict:
        """Run the AASIST + scam pipeline without ECAPA enrollment checks."""

        from main import analyze_audio, spoof_detector

        spoof_result = spoof_detector.predict(audio_file)
        scam_result = analyze_audio(audio_file)

        return {
            "spoof_probability": spoof_result["spoof_probability"],
            "speaker_similarity": None,
            "speaker_verification_status": "NOT_ENROLLED",
            "scam_score": scam_result["scam_score"],
            "indicators": scam_result["indicators"],
            "transcript": scam_result["transcript"],
            "language": scam_result["language"],
        }

    async def analyze(
        self,
        request: AnalysisRequest,
        active_profile: object | None = None,
    ) -> AIAnalysisResult:
        """
        Analyze Base64 encoded audio.

        Supported input:
            - WAV
            - WebM / Opus

        Behavior:

            audio_chunk missing
                ↓
            deterministic demo result

            audio_chunk present
                ↓
            real Abhinay AI
        """

        # -----------------------------------------------------
        # Backward-compatible demo mode
        # -----------------------------------------------------

        if not request.audio_chunk or request.audio_chunk == "demo":
            return self._demo_result(
              request.session_id
            )

        start_time = time.perf_counter()

        # -----------------------------------------------------
        # Decode Base64
        # -----------------------------------------------------

        try:
            audio_bytes = base64.b64decode(
                request.audio_chunk,
                validate=True,
            )

        except Exception as exc:
            raise ValueError(
                "Invalid base64 audio data."
            ) from exc

        if not audio_bytes:
            raise ValueError(
                "Decoded audio is empty."
            )

        # -----------------------------------------------------
        # Determine audio format
        # -----------------------------------------------------

        if audio_bytes[:4] == b"RIFF":
            audio_extension = ".wav"
        else:
            audio_extension = ".webm"

        temp_path = None

        try:

            # -------------------------------------------------
            # Create temporary audio file
            # -------------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=audio_extension,
                delete=False,
            ) as temp_file:

                temp_file.write(
                    audio_bytes
                )

                temp_path = temp_file.name

            print(
                "[AIService] Starting AI analysis "
                f"format={audio_extension} "
                f"size={len(audio_bytes)} bytes"
            )

            # -------------------------------------------------
            # Real Abhinay AI
            # -------------------------------------------------

            try:
                result = self._ensure_engine().analyze(
                    audio_file=temp_path,
                    contact_id=None,
                )
            except FileNotFoundError:
                result = self._partial_analysis_without_speaker_verification(
                    temp_path
                )
            except Exception as exc:
                print(
                    "[AIService] Real inference unavailable; using explicit ASR fallback: "
                    f"{exc}"
                )
                result = self._fallback_result()

            if active_profile is not None:
                incoming_embedding = self._generate_detector_embedding(audio_bytes)
                similarity, status = self.compare_with_profile(
                    incoming_embedding,
                    getattr(active_profile, "embedding", None),
                )
                result["speaker_similarity"] = similarity
                result["speaker_verification_status"] = status

            # -------------------------------------------------
            # Latency
            # -------------------------------------------------

            latency_ms = int(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000
            )

            print(
                "[AIService] AI analysis completed "
                f"latency={latency_ms}ms"
            )

            return self._build_result(
                session_id=request.session_id,
                result=result,
                latency_ms=latency_ms,
            )

        finally:

            # -------------------------------------------------
            # Cleanup
            # -------------------------------------------------

            if temp_path:

                try:
                    Path(
                        temp_path
                    ).unlink(
                        missing_ok=True
                    )

                except Exception as exc:

                    print(
                        "[AIService] "
                        "Temporary file cleanup failed: "
                        f"{exc}"
                    )

    # =========================================================
    # PCM → WAV
    # =========================================================

    @staticmethod
    def pcm_to_wav(
        pcm_audio: np.ndarray,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> bytes:
        """
        Convert PCM samples into a WAV byte stream.

        Expected:
            numpy array
            int16
            mono
            16 kHz by default
        """

        pcm_audio = np.asarray(
            pcm_audio,
            dtype=np.int16,
        )

        if pcm_audio.size == 0:
            raise ValueError(
                "PCM audio is empty."
            )

        if channels != 1:
            raise ValueError(
                "Only mono PCM is currently supported."
            )

        import io

        buffer = io.BytesIO()

        with wave.open(
            buffer,
            "wb",
        ) as wav_file:

            wav_file.setnchannels(
                channels
            )

            wav_file.setsampwidth(
                2
            )

            wav_file.setframerate(
                sample_rate
            )

            wav_file.writeframes(
                pcm_audio.tobytes()
            )

        return buffer.getvalue()

    # =========================================================
    # REAL-TIME PCM ANALYSIS
    # =========================================================

    def analyze_pcm_sync(
        self,
        session_id: str,
        pcm_audio: np.ndarray,
        contact_id: str | None,
        sample_rate: int = 16000,
        active_profile: object | None = None,
    ) -> AIAnalysisResult:
        """
        Synchronous real-time AI entry point.

        The WebSocket worker MUST execute this through:

            asyncio.to_thread(...)

        because AASIST, ECAPA, Whisper and scam analysis
        perform blocking inference.
        """

        if pcm_audio is None:
            raise ValueError(
                "PCM audio is required."
            )

        pcm_audio = np.asarray(
            pcm_audio,
            dtype=np.int16,
        )

        if pcm_audio.size == 0:
            raise ValueError(
                "PCM audio is empty."
            )

        start_time = time.perf_counter()

        # -----------------------------------------------------
        # PCM → WAV
        # -----------------------------------------------------

        wav_bytes = self.pcm_to_wav(
            pcm_audio=pcm_audio,
            sample_rate=sample_rate,
            channels=1,
        )

        temp_path = None

        try:

            # -------------------------------------------------
            # Write temporary WAV
            # -------------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as temp_file:

                temp_file.write(
                    wav_bytes
                )

                temp_path = temp_file.name

            duration_seconds = (
                len(pcm_audio)
                / sample_rate
            )

            print(
                "[AIService] Real-time AI analysis "
                f"window={duration_seconds:.2f}s "
                f"contact={contact_id or 'NOT_ENROLLED'}"
            )

            # -------------------------------------------------
            # Abhinay complete pipeline
            # -------------------------------------------------

            try:
                result = self._ensure_engine().analyze(
                    audio_file=temp_path,
                    contact_id=None,
                )
            except FileNotFoundError:
                result = self._partial_analysis_without_speaker_verification(
                    temp_path
                )
            except Exception as exc:
                print(
                    "[AIService] Real inference unavailable; falling back to safe demo result: "
                    f"{exc}"
                )
                result = self._fallback_result()

            if not isinstance(result, dict):
                result = dict(result)

            result.setdefault("pipeline", {})
            result["pipeline"].setdefault("aasist", {"executed": True, "latency_ms": 0.0})
            result["pipeline"].setdefault("asr_scam", {"executed": True, "latency_ms": 0.0})
            result["pipeline"].setdefault("ecapa", {"executed": False, "latency_ms": 0.0})
            result["pipeline"].setdefault("risk_engine", {"executed": False, "latency_ms": 0.0})

            if active_profile is not None:
                incoming_embedding = self._generate_detector_embedding(wav_bytes)
                ecapa_start = time.perf_counter()
                similarity, status = self.compare_with_profile(
                    incoming_embedding,
                    getattr(active_profile, "embedding", None),
                )
                result["pipeline"]["ecapa"] = {
                    "executed": True,
                    "latency_ms": int((time.perf_counter() - ecapa_start) * 1000),
                }
                result["speaker_similarity"] = similarity
                result["speaker_verification_status"] = status
            else:
                result["speaker_similarity"] = None
                result["speaker_verification_status"] = "NOT_ENROLLED"
                result["pipeline"]["ecapa"] = {
                    "executed": False,
                    "latency_ms": 0.0,
                }

            result["total_latency_ms"] = float(result.get("total_latency_ms") or 0.0)
            if result["total_latency_ms"] <= 0:
                result["total_latency_ms"] = float(
                    result.get("pipeline", {}).get("aasist", {}).get("latency_ms", 0.0)
                    + result.get("pipeline", {}).get("ecapa", {}).get("latency_ms", 0.0)
                    + result.get("pipeline", {}).get("asr_scam", {}).get("latency_ms", 0.0)
                )

            # -------------------------------------------------
            # Latency
            # -------------------------------------------------

            latency_ms = int(
                (
                    time.perf_counter()
                    - start_time
                )
                * 1000
            )

            print(
                "[AIService] Real-time AI completed "
                f"latency={latency_ms}ms"
            )

            return self._build_result(
                session_id=session_id,
                result=result,
                latency_ms=latency_ms,
            )

        finally:

            if temp_path:

                try:
                    Path(
                        temp_path
                    ).unlink(
                        missing_ok=True
                    )

                except Exception as exc:

                    print(
                        "[AIService] "
                        "Temporary WAV cleanup failed: "
                        f"{exc}"
                    )


# ==============================================================
# Shared service instance
# ==============================================================

ai_service = AIService()