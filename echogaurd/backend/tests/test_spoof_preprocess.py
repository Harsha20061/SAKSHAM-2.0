import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
VOICE_SECURITY_ROOT = PROJECT_ROOT / "VoiceSecurity"
if str(VOICE_SECURITY_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_SECURITY_ROOT))

from module1_spoof import preprocess


AUDIO_DIR = VOICE_SECURITY_ROOT / "audio"


def test_load_audio_bypasses_conversion_for_compatible_wav(monkeypatch):
    def conversion_must_not_run(_audio_path):
        raise AssertionError("FFmpeg conversion should be bypassed")

    monkeypatch.setattr(preprocess, "convert_to_wav", conversion_must_not_run)

    audio = preprocess.load_audio(str(AUDIO_DIR / "genuine_fixed.wav"))

    assert audio.dtype == np.float32
    assert audio.size > 0


def test_load_audio_keeps_conversion_for_incompatible_audio(monkeypatch):
    conversion_calls = []
    original_convert_to_wav = preprocess.convert_to_wav

    def record_conversion(audio_path):
        conversion_calls.append(audio_path)
        return original_convert_to_wav(audio_path)

    monkeypatch.setattr(preprocess, "convert_to_wav", record_conversion)

    audio = preprocess.load_audio(str(AUDIO_DIR / "genuine.wav"))

    assert conversion_calls == [str(AUDIO_DIR / "genuine.wav")]
    assert audio.dtype == np.float32
    assert audio.size > 0
