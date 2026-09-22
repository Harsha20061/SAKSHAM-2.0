import numpy as np

from app.services.audio_buffer import (
    RollingAudioBuffer,
)


def test_empty_buffer():

    buffer = RollingAudioBuffer()

    assert len(buffer) == 0
    assert buffer.duration_seconds() == 0.0


def test_append_audio():

    buffer = RollingAudioBuffer(
        max_seconds=2
    )

    audio = np.zeros(
        16000,
        dtype=np.int16,
    )

    buffer.append(audio)

    assert len(buffer) == 16000
    assert buffer.duration_seconds() == 1.0


def test_buffer_keeps_latest_audio():

    buffer = RollingAudioBuffer(
        max_seconds=2
    )

    audio = np.arange(
        16000 * 5,
        dtype=np.int16,
    )

    buffer.append(audio)

    assert len(buffer) == 32000
    assert buffer.duration_seconds() == 2.0

    result = buffer.get_audio()

    assert result.size == 32000


def test_clear():

    buffer = RollingAudioBuffer()

    audio = np.ones(
        16000,
        dtype=np.int16,
    )

    buffer.append(audio)

    assert len(buffer) == 16000

    buffer.clear()

    assert len(buffer) == 0
    assert buffer.duration_seconds() == 0.0