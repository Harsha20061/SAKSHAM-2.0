import numpy as np


TARGET_SAMPLE_RATE = 16000
DEFAULT_MAX_SECONDS = 10


class RollingAudioBuffer:
    """
    Maintains a rolling window of model-ready audio.

    Audio format:
        Sample rate: 16 kHz
        Channels: mono
        Format: int16 PCM
    """

    def __init__(
        self,
        max_seconds: int = DEFAULT_MAX_SECONDS,
    ):
        if max_seconds <= 0:
            raise ValueError(
                "max_seconds must be greater than 0"
            )

        self.max_samples = (
            TARGET_SAMPLE_RATE * max_seconds
        )

        self.buffer = np.empty(
            0,
            dtype=np.int16,
        )

    def append(
        self,
        pcm: np.ndarray,
    ) -> None:

        if pcm is None or pcm.size == 0:
            return

        pcm = np.asarray(
            pcm,
            dtype=np.int16,
        )

        self.buffer = np.concatenate(
            (
                self.buffer,
                pcm,
            )
        )

        # Keep only the newest audio.
        if self.buffer.size > self.max_samples:

            self.buffer = self.buffer[
                -self.max_samples:
            ]

    def get_audio(self) -> np.ndarray:
        """Return a copy of the current PCM buffer."""

        return self.buffer.copy()

    def get_latest_window(self, seconds: int) -> np.ndarray:
        """Return a bounded latest PCM window from the rolling source."""

        if seconds <= 0:
            raise ValueError("seconds must be greater than 0")

        window_samples = TARGET_SAMPLE_RATE * seconds
        return self.buffer[-window_samples:].copy()

    def duration_seconds(self) -> float:

        if self.buffer.size == 0:
            return 0.0

        return (
            self.buffer.size
            / TARGET_SAMPLE_RATE
        )

    def clear(self) -> None:

        self.buffer = np.empty(
            0,
            dtype=np.int16,
        )

    def __len__(self) -> int:

        return self.buffer.size