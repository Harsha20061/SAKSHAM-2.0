import time
from typing import Any


SCENARIOS: dict[str, dict[str, Any]] = {
    "LOW": {
        "spoof_probability": 0.12,
        "speaker_similarity": 0.94,
        "scam_score": 0.08,
        "indicators": [],
    },
    "SUSPICIOUS": {
        "spoof_probability": 0.52,
        "speaker_similarity": 0.61,
        "scam_score": 0.48,
        "indicators": [
            "unusual_voice_pattern",
            "moderate_speaker_mismatch",
        ],
    },
    "HIGH": {
        "spoof_probability": 0.92,
        "speaker_similarity": 0.21,
        "scam_score": 0.88,
        "indicators": [
            "possible_synthetic_voice",
            "speaker_mismatch",
            "urgent_money_request",
        ],
    },
}


class MockAnalysisService:
    """
    Temporary AI service for EchoGuard development.

    This will later be replaced by Abhinay's actual
    voice anti-spoofing / speaker verification / scam
    analysis pipeline.
    """

    @staticmethod
    async def analyze(
        scenario: str = "LOW",
    ) -> dict[str, Any]:

        start_time = time.perf_counter()

        scenario = scenario.upper()

        if scenario not in SCENARIOS:
            scenario = "LOW"

        data = SCENARIOS[scenario]

        # Simulated model latency.
        await _simulate_model_latency()

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        return {
            "spoof_probability": data[
                "spoof_probability"
            ],
            "speaker_similarity": data[
                "speaker_similarity"
            ],
            "scam_score": data[
                "scam_score"
            ],
            "indicators": list(
                data["indicators"]
            ),
            "latency_ms": round(
                latency_ms,
                2,
            ),
        }


async def _simulate_model_latency() -> None:
    """
    Simulate a small AI inference delay.

    We keep this intentionally lightweight so
    development remains fast.
    """
    import asyncio

    await asyncio.sleep(0.08)