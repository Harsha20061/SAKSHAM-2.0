import time
import threading

import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from module3_scam.scam_detector import detect_scam


MODEL_NAME = "tiny"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
CPU_THREADS = 2
BEAM_SIZE = 1

_model = None
_warmup_lock = threading.RLock()
_warmed_up = False


def _get_model() -> WhisperModel:
    global _model

    if _model is None:
        if WhisperModel is None:
            raise RuntimeError(
                "faster-whisper is required for ASR inference."
            )

        with _warmup_lock:
            if _model is None:
                _model = WhisperModel(
                    MODEL_NAME,
                    device=DEVICE,
                    compute_type=COMPUTE_TYPE,
                    cpu_threads=CPU_THREADS,
                    num_workers=1,
                )

    return _model


def warmup_model() -> None:
    """Load and execute one small inference before live analysis."""

    global _warmed_up

    if _warmed_up:
        return

    with _warmup_lock:
        if _warmed_up:
            return

        model = _get_model()
        warmup_audio = np.zeros(16000, dtype=np.float32)
        segments, _ = model.transcribe(
            warmup_audio,
            language=None,
            beam_size=BEAM_SIZE,
            condition_on_previous_text=False,
            vad_filter=True,
        )
        list(segments)
        _warmed_up = True


def _has_voice_activity(audio_file: str) -> bool:
    """Reject only effectively silent windows before invoking Whisper."""

    import wave

    with wave.open(audio_file, "rb") as wav_file:
        frames = wav_file.readframes(wav_file.getnframes())

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if audio.size == 0:
        return False

    rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))
    return rms >= 0.003


def analyze_audio(audio_file):
    """
    Convert speech to text and detect scam intent.
    """

    start_time = time.perf_counter()

    warmup_model()

    if not _has_voice_activity(audio_file):
        return {
            "transcript": "",
            "language": None,
            "language_confidence": None,
            "scam_score": 0.0,
            "indicators": [],
            "latency_ms": int((time.perf_counter() - start_time) * 1000),
            "asr_executed": False,
            "asr_error": "No speech activity detected",
            "asr_fallback": False,
        }

    # Speech-to-text. Whisper retains automatic language detection.
    model = _get_model()
    segments, info = model.transcribe(
        audio_file,
        language=None,
        beam_size=BEAM_SIZE,
        condition_on_previous_text=False,
        vad_filter=True,
    )
    segments = list(segments)

    transcript = " ".join(
        segment.text.strip()
        for segment in segments
        if segment.text.strip()
    ).strip()
    language = info.language
    language_confidence = info.language_probability

    # Scam detection
    scam_result = detect_scam(transcript)

    latency_ms = int(
        (time.perf_counter() - start_time) * 1000
    )

    return {
        "transcript": transcript,
        "language": language,
        "scam_score": scam_result["scam_score"],
        "indicators": scam_result["indicators"],
        "language_confidence": language_confidence,
        "latency_ms": latency_ms
        ,
        "asr_executed": True,
        "asr_error": None,
        "asr_fallback": False,
    }


if __name__ == "__main__":

    audio_file = "audio/scam_test_fixed.wav"

    result = analyze_audio(audio_file)

    print("\nModule 3 Result")
    print("----------------")

    print("Transcript:")
    print(result["transcript"])

    print("\nLanguage:")
    print(result["language"])

    print("\nScam Score:")
    print(result["scam_score"])

    print("\nIndicators:")
    print(result["indicators"])

    print("\nLatency:")
    print(result["latency_ms"], "ms")