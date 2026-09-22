import concurrent.futures
import asyncio

import numpy as np

from app.services import ai_service as ai_service_module
from app.services.audio_buffer import RollingAudioBuffer


def test_asr_model_is_singleton(monkeypatch):
    created = []

    class FakeModel:
        def __init__(self, *args, **kwargs):
            created.append((args, kwargs))

    monkeypatch.setattr(
        "module3_scam.speech_to_text.WhisperModel",
        FakeModel,
    )

    import module3_scam.speech_to_text as speech_to_text

    monkeypatch.setattr(speech_to_text, "_model", None)
    first = speech_to_text._get_model()
    second = speech_to_text._get_model()

    assert first is second
    assert len(created) == 1
    assert created[0][1]["compute_type"] == "int8"
    assert created[0][1]["cpu_threads"] == 2


def test_asr_model_is_not_created_concurrently(monkeypatch):
    created = []

    class FakeModel:
        def __init__(self, *args, **kwargs):
            created.append((args, kwargs))

    monkeypatch.setattr(
        "module3_scam.speech_to_text.WhisperModel",
        FakeModel,
    )

    import module3_scam.speech_to_text as speech_to_text

    monkeypatch.setattr(speech_to_text, "_model", None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        models = list(executor.map(lambda _: speech_to_text._get_model(), range(4)))

    assert len(created) == 1
    assert len({id(model) for model in models}) == 1


def test_rolling_buffer_returns_latest_window():
    buffer = RollingAudioBuffer(max_seconds=10)
    audio = np.arange(16000 * 8, dtype=np.int16)
    buffer.append(audio)

    window = buffer.get_latest_window(5)

    assert window.size == 16000 * 5
    np.testing.assert_array_equal(window, audio[-16000 * 5:])


def test_fallback_result_marks_asr_unexecuted():
    result = ai_service_module.AIService._fallback_result()

    assert result["pipeline"]["asr_scam"] == {
        "executed": False,
        "latency_ms": 0.0,
        "error": "ASR inference unavailable",
        "fallback": True,
    }


def test_ai_service_warmup_initializes_engine_and_asr(monkeypatch):
    service = ai_service_module.AIService.__new__(
        ai_service_module.AIService
    )
    service.engine = None
    service.ready = False

    engine = object()
    asr_warmup = []

    monkeypatch.setattr(
        service,
        "_ensure_engine",
        lambda: engine,
    )

    import module3_scam.speech_to_text as speech_to_text

    monkeypatch.setattr(
        speech_to_text,
        "warmup_model",
        lambda: asr_warmup.append(True),
    )

    service.warmup()

    assert service.ready is True
    assert asr_warmup == [True]


def test_startup_warmup_runs_off_event_loop(monkeypatch):
    import app.main as app_main

    calls = []

    async def fake_init_db():
        calls.append("db")

    def fake_warmup():
        calls.append("ai")

    monkeypatch.setattr(app_main, "init_db", fake_init_db)
    monkeypatch.setattr(app_main.ai_service, "warmup", fake_warmup)

    asyncio.run(app_main.startup_event())

    assert calls == ["db", "ai"]
