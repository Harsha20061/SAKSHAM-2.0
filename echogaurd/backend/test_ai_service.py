import asyncio
import base64
import json
from pathlib import Path

from app.models.schemas import AnalysisRequest
from app.services.ai_service import ai_service


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIO_FILE = REPOSITORY_ROOT / "VoiceSecurity" / "audio" / "scam_test.wav"


async def main():
    print("\n=== EchoGuard -> Abhinay AI Integration Test ===")

    audio_bytes = AUDIO_FILE.read_bytes()

    encoded_audio = base64.b64encode(
        audio_bytes
    ).decode("utf-8")

    request = AnalysisRequest(
        session_id="integration-test-001",
        audio_chunk=encoded_audio,
        contact_id="abhinay",
    )

    print(f"Audio file: {AUDIO_FILE}")
    print(f"Audio size: {len(audio_bytes)} bytes")
    print("Sending audio to AIService...\n")

    result = await ai_service.analyze(request)

    print("\n=== ECHOGUARD AI RESULT ===")
    print(
        json.dumps(
            result.model_dump(),
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())