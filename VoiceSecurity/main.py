import json
import time

from module1_spoof.inference import AASISTDetector
from module2_speaker.matching import compare_voice
from module3_scam.speech_to_text import analyze_audio


# ============================================================
# LOAD HEAVY AI MODELS ONCE
# ============================================================

print("Initializing Voice Security AI Engine...")

spoof_detector = AASISTDetector()

print("Voice Security AI Engine ready.")


# ============================================================
# COMPLETE PIPELINE
# ============================================================

def analyze_call(audio_file, contact_id=None):
    """
    Run the complete voice-security analysis pipeline.

    Modules:
        1. AASIST  -> spoof detection
        2. ECAPA   -> trusted speaker verification (optional)
        3. Whisper -> speech-to-text
        4. Scam detector -> social-engineering analysis
    """

    total_start = time.perf_counter()

    # --------------------------------------------------------
    # Module 1: Spoof Detection
    # --------------------------------------------------------

    print("[Pipeline] AASIST START")
    aasist_start = time.perf_counter()
    spoof_result = spoof_detector.predict(audio_file)
    aasist_latency_ms = int((time.perf_counter() - aasist_start) * 1000)
    print(f"[Pipeline] AASIST END spoof_probability={spoof_result['spoof_probability']} latency_ms={aasist_latency_ms}")

    # --------------------------------------------------------
    # Module 2: Speaker Verification
    # --------------------------------------------------------

    ecapa_latency_ms = 0
    if contact_id:
        print("[Pipeline] ECAPA START")
        ecapa_start = time.perf_counter()
        speaker_result = compare_voice(
            audio_file,
            contact_id
        )
        ecapa_latency_ms = int((time.perf_counter() - ecapa_start) * 1000)
        speaker_similarity = speaker_result["speaker_similarity"]
        speaker_verification_status = "VERIFIED" if speaker_similarity >= 0.75 else "MISMATCH"
        print(f"[Pipeline] ECAPA END similarity={speaker_similarity} status={speaker_verification_status} latency_ms={ecapa_latency_ms}")
    else:
        speaker_similarity = None
        speaker_verification_status = "NOT_ENROLLED"
        print("[Pipeline] ECAPA SKIPPED no_active_profile")

    # --------------------------------------------------------
    # Module 3: Speech-to-Text + Scam Detection
    # --------------------------------------------------------

    print("[Pipeline] ASR_SCAM START")
    asr_start = time.perf_counter()
    scam_result = analyze_audio(audio_file)
    asr_latency_ms = int((time.perf_counter() - asr_start) * 1000)
    print(f"[Pipeline] ASR_SCAM END scam_score={scam_result['scam_score']} indicators={scam_result['indicators']} latency_ms={asr_latency_ms}")

    # --------------------------------------------------------
    # Total Pipeline Latency
    # --------------------------------------------------------

    total_latency_ms = int(
        (time.perf_counter() - total_start) * 1000
    )

    # --------------------------------------------------------
    # Unified AI Output
    # --------------------------------------------------------

    result = {
        "spoof_probability": spoof_result["spoof_probability"],
        "speaker_similarity": speaker_similarity,
        "speaker_verification_status": speaker_verification_status,
        "scam_score": scam_result["scam_score"],
        "indicators": scam_result["indicators"],
        "transcript": scam_result["transcript"],
        "language": scam_result["language"],
        "language_confidence": scam_result.get("language_confidence"),
        "latency_ms": total_latency_ms,
        "total_latency_ms": total_latency_ms,
        "aasist_latency_ms": aasist_latency_ms,
        "ecapa_latency_ms": ecapa_latency_ms,
        "asr_latency_ms": asr_latency_ms,
        "scam_latency_ms": asr_latency_ms,
        "pipeline": {
            "aasist": {"executed": True, "latency_ms": aasist_latency_ms},
            "ecapa": {"executed": bool(contact_id), "latency_ms": ecapa_latency_ms},
            "asr_scam": {
                "executed": bool(scam_result.get("asr_executed", True)),
                "latency_ms": scam_result.get("latency_ms", asr_latency_ms),
                "error": scam_result.get("asr_error"),
                "fallback": bool(scam_result.get("asr_fallback", False)),
            },
            "risk_engine": {"executed": False, "latency_ms": 0},
        },
    }

    return result


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    audio_file = "audio/scam_test_fixed.wav"

    contact_id = "abhinay"

    result = analyze_call(
        audio_file,
        contact_id
    )

    print("\n")
    print("========================================")
    print("       VOICE SECURITY ANALYSIS")
    print("========================================")

    print("\nModule 1 - Spoof Detection")
    print("----------------------------------------")
    print(
        "Spoof Probability :",
        result["spoof_probability"]
    )

    print("\nModule 2 - Speaker Verification")
    print("----------------------------------------")
    print(
        "Speaker Similarity:",
        result["speaker_similarity"]
    )

    print("\nModule 3 - Scam Detection")
    print("----------------------------------------")
    print(
        "Scam Score        :",
        result["scam_score"]
    )

    print(
        "Indicators        :",
        result["indicators"]
    )

    print("\nSpeech-to-Text")
    print("----------------------------------------")

    print(
        "Transcript        :",
        result["transcript"]
    )

    print(
        "Language          :",
        result["language"]
    )

    print("\nTotal Latency")
    print("----------------------------------------")

    print(
        result["latency_ms"],
        "ms"
    )

    print("\nJSON Output")
    print("----------------------------------------")

    print(
        json.dumps(
            result,
            indent=4
        )
    )

    print("\n========================================")