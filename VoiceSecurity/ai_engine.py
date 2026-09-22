import time
from typing import Any, Dict

from main import analyze_call


class VoiceSecurityEngine:
    """
    Adapter around Abhinay's complete AI pipeline.

    This class provides a stable interface for EchoGuard.
    """

    def analyze(
        self,
        audio_file: str,
        contact_id: str | None
    ) -> Dict[str, Any]:

        start_time = time.perf_counter()

        result = analyze_call(
            audio_file,
            contact_id
        )

        adapter_latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        result_payload = {
            "spoof_probability": float(
                result["spoof_probability"]
            ),

            "speaker_similarity": (
                float(result["speaker_similarity"])
                if result.get("speaker_similarity") is not None
                else None
            ),

            "speaker_verification_status": result.get(
                "speaker_verification_status",
                "NOT_ENROLLED",
            ),

            "scam_score": float(
                result["scam_score"]
            ),

            "indicators": list(
                result["indicators"]
            ),

            "transcript": result.get(
                "transcript",
                ""
            ),

            "language": result.get(
                "language"
            ),
            "language_confidence": result.get(
                "language_confidence"
            ),

            "latency_ms": adapter_latency_ms,
            "total_latency_ms": result.get("total_latency_ms", adapter_latency_ms),
            "pipeline": result.get("pipeline", {
                "aasist": {"executed": True, "latency_ms": 0},
                "ecapa": {"executed": False, "latency_ms": 0},
                "asr_scam": {"executed": True, "latency_ms": 0},
                "risk_engine": {"executed": False, "latency_ms": 0},
            }),
            "aasist_latency_ms": result.get("aasist_latency_ms", 0),
            "ecapa_latency_ms": result.get("ecapa_latency_ms", 0),
            "asr_latency_ms": result.get("asr_latency_ms", 0),
            "scam_latency_ms": result.get("scam_latency_ms", 0),
        }

        return result_payload


# ------------------------------------------------------------
# Singleton engine
# ------------------------------------------------------------

_engine = None


def get_engine() -> VoiceSecurityEngine:
    """
    Return the shared VoiceSecurityEngine instance.
    """

    global _engine

    if _engine is None:
        _engine = VoiceSecurityEngine()

    return _engine