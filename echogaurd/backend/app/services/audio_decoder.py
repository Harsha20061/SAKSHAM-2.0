import io
from typing import Optional

import av
import numpy as np


TARGET_SAMPLE_RATE = 16000
TARGET_CHANNEL_LAYOUT = "mono"
TARGET_SAMPLE_FORMAT = "s16"


class AudioDecodeError(Exception):
    """Raised when compressed audio cannot be decoded."""


def decode_audio_to_pcm(
    audio_bytes: bytes,
) -> Optional[np.ndarray]:
    """
    Decode WebM/Opus or other supported container audio
    into mono 16 kHz signed 16-bit PCM.

    Returns:
        NumPy array with shape (samples,)
        and dtype int16.

    Returns None if the supplied data does not yet contain
    enough decodable audio.
    """

    if not audio_bytes:
        return None

    container = None

    try:
        input_buffer = io.BytesIO(audio_bytes)

        # Let FFmpeg/PyAV detect the container.
        # This supports WebM/Opus and avoids hard-coding
        # the browser MIME type.
        container = av.open(
            input_buffer,
            mode="r",
        )

        resampler = av.audio.resampler.AudioResampler(
            format=TARGET_SAMPLE_FORMAT,
            layout=TARGET_CHANNEL_LAYOUT,
            rate=TARGET_SAMPLE_RATE,
        )

        pcm_chunks: list[np.ndarray] = []

        for frame in container.decode(audio=0):

            resampled = resampler.resample(frame)

            if resampled is None:
                continue

            if not isinstance(resampled, list):
                resampled = [resampled]

            for resampled_frame in resampled:

                if resampled_frame is None:
                    continue

                array = resampled_frame.to_ndarray()

                if array.size == 0:
                    continue

                # Mono audio normally arrives as:
                # (1, samples)
                if array.ndim == 2:
                    array = array[0]

                array = np.asarray(
                    array,
                    dtype=np.int16,
                )

                pcm_chunks.append(array)

        if not pcm_chunks:
            return None

        return np.concatenate(pcm_chunks)

    except (
        av.error.InvalidDataError,
        av.error.EOFError,
        av.error.OSError,
    ) as exc:

        # This can happen when a WebM stream is still
        # incomplete. More chunks may make it decodable.
        print(
            "[AudioDecoder] "
            f"Waiting for more audio: {exc}"
        )

        return None

    except Exception as exc:

        raise AudioDecodeError(
            f"Failed to decode audio: {exc}"
        ) from exc

    finally:

        if container is not None:
            container.close()


def pcm_duration_seconds(
    pcm: np.ndarray,
) -> float:
    """Return PCM duration assuming 16 kHz audio."""

    if pcm is None or pcm.size == 0:
        return 0.0

    return pcm.size / TARGET_SAMPLE_RATE