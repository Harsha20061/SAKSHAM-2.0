import os
import subprocess
import tempfile
import wave

import numpy as np
import librosa


TARGET_SR = 16000
SEGMENT_SAMPLES = 64600  # ~4.04 seconds


def convert_to_wav(input_file):
    """
    Automatically convert any supported audio format
    to 16 kHz mono PCM WAV using FFmpeg.
    """

    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Audio file not found: {input_file}"
        )

    # Create temporary WAV file
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    )

    output_file = temp_file.name
    temp_file.close()

    command = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-ar", str(TARGET_SR),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_file
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                "FFmpeg conversion failed:\n"
                + result.stderr
            )

        return output_file

    except FileNotFoundError:
        raise RuntimeError(
            "FFmpeg was not found. "
            "Make sure FFmpeg is installed and available in PATH."
        )


def load_audio(file_path):
    """
    Automatically convert audio to WAV and load it.
    """

    if file_path.lower().endswith(".wav"):
        try:
            with wave.open(file_path, "rb") as wav_file:
                is_target_format = (
                    wav_file.getnchannels() == 1
                    and wav_file.getframerate() == TARGET_SR
                    and wav_file.getsampwidth() == 2
                )
        except (OSError, wave.Error):
            is_target_format = False

        if is_target_format:
            audio, sr = librosa.load(
                file_path,
                sr=TARGET_SR,
                mono=True,
            )
            return audio.astype(np.float32)

    converted_file = convert_to_wav(file_path)

    try:
        audio, sr = librosa.load(
            converted_file,
            sr=TARGET_SR,
            mono=True
        )

        audio = audio.astype(np.float32)

        return audio

    finally:
        # Delete temporary converted WAV
        if os.path.exists(converted_file):
            os.remove(converted_file)


def create_segments(audio):
    """
    Split audio into fixed-size segments required by AASIST.
    """

    segments = []

    if len(audio) == 0:
        raise ValueError("Audio file contains no audio data.")

    if len(audio) < SEGMENT_SAMPLES:

        repeat_count = int(
            np.ceil(
                SEGMENT_SAMPLES / len(audio)
            )
        )

        audio = np.tile(
            audio,
            repeat_count
        )

    for start in range(
        0,
        len(audio) - SEGMENT_SAMPLES + 1,
        SEGMENT_SAMPLES
    ):

        segment = audio[
            start:start + SEGMENT_SAMPLES
        ]

        segments.append(segment)

    return segments


if __name__ == "__main__":

    # You can give this ANY supported audio file.
    audio_file = "audio/test.wav"

    print("Input file:", audio_file)
    print("Converting audio automatically...")

    audio = load_audio(audio_file)

    print("Audio loaded successfully")
    print("Sample rate:", TARGET_SR, "Hz")
    print("Total samples:", len(audio))
    print(
        "Duration:",
        round(len(audio) / TARGET_SR, 3),
        "seconds"
    )

    segments = create_segments(audio)

    print(
        "Number of segments:",
        len(segments)
    )

    for i, segment in enumerate(segments):

        print(
            f"Segment {i + 1}: "
            f"{len(segment)} samples "
            f"({len(segment) / TARGET_SR:.2f} sec)"
        )