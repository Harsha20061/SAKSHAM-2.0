import asyncio
import uuid
import wave
from pathlib import Path

import numpy as np

from app.api.routes.analysis import run_real_analysis

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIO_PATH = PROJECT_ROOT / "VoiceSecurity" / "audio" / "genuine_fixed.wav"


class RecordingWebSocket:
    def __init__(self, stop_event, target_results):
        self.stop_event = stop_event
        self.target_results = target_results
        self.sent = []
        self.result_event = asyncio.Event()

    async def send_json(self, payload):
        self.sent.append(payload)
        if payload.get("type") == "analysis_result":
            results = [msg for msg in self.sent if msg.get("type") == "analysis_result"]
            self.result_event.set()
            if len(results) >= self.target_results:
                self.stop_event.set()


def test_analysis_websocket_emits_multiple_real_results_for_overlapping_windows():
    with wave.open(str(AUDIO_PATH), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        pcm = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype=np.int16)

    windows = []
    for start in (0, 2, 4, 6):
        start_index = start * sample_rate
        end_index = start_index + (5 * sample_rate)
        chunk = pcm[start_index:end_index]
        if chunk.size > 0:
            windows.append(chunk)

    stop_event = asyncio.Event()
    websocket = RecordingWebSocket(stop_event, target_results=3)
    result_state = {"sequence": 0, "last_window_signature": None}
    audio_ready_event = asyncio.Event()
    current_index = {"value": 0}

    def get_audio_window():
        if current_index["value"] >= len(windows):
            return None
        return windows[current_index["value"]]

    async def wait_for_results(count):
        async def has_enough_results():
            return sum(
                message.get("type") == "analysis_result"
                for message in websocket.sent
            ) >= count

        while not await has_enough_results():
            websocket.result_event.clear()
            try:
                await asyncio.wait_for(
                    websocket.result_event.wait(),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                raise AssertionError(
                    f"Timed out waiting for analysis_result {count}"
                )

    async def feed_windows():
        for index in range(len(windows[:3])):
            current_index["value"] = index
            audio_ready_event.set()
            await wait_for_results(index + 1)

    async def _run_once():
        task = asyncio.create_task(
            run_real_analysis(
                websocket=websocket,
                session_id="session-stream",
                contact_id=None,
                stop_event=stop_event,
                audio_ready_event=audio_ready_event,
                get_audio_window=get_audio_window,
                active_profile=None,
                result_state=result_state,
            )
        )
        await feed_windows()
        await task

    asyncio.run(_run_once())

    results = [msg for msg in websocket.sent if msg.get("type") == "analysis_result"]
    assert len(results) >= 3, f"Expected >= 3 analysis_result messages, got {len(results)}"

    sequence_numbers = [msg["sequence_number"] for msg in results]
    assert sequence_numbers == sorted(sequence_numbers)
    assert len(set(sequence_numbers)) == len(sequence_numbers)

    for msg in results:
        payload = msg["payload"]
        assert msg["timestamp"]
        assert payload["spoof_probability"] >= 0.0 and payload["spoof_probability"] <= 1.0
        assert payload["speaker_similarity"] is None or 0.0 <= payload["speaker_similarity"] <= 1.0
        assert payload["speaker_verification_status"] in {"VERIFIED", "MISMATCH", "NOT_ENROLLED"}
        assert payload["scam_score"] >= 0.0 and payload["scam_score"] <= 1.0
        assert payload["risk_score"] >= 0.0 and payload["risk_score"] <= 1.0
        assert payload["risk_level"] in {"LOW", "SUSPICIOUS", "HIGH"}
        assert isinstance(payload["indicators"], list)
