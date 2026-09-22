import numpy as np
import torch
import librosa
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy

from pathlib import Path

MODEL_DIR = str(
    Path(__file__).resolve().parents[1]
    / "models"
    / "ecapa"
)
TARGET_SR = 16000

# Load ECAPA-TDNN model
model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=MODEL_DIR,
    run_opts={"device": "cpu"},
    local_strategy=LocalStrategy.COPY
)


def extract_embedding(audio_file):
    """
    Extract ECAPA-TDNN speaker embedding from an audio file.
    """

    # Load audio as 16 kHz mono
    audio, sample_rate = librosa.load(
        audio_file,
        sr=TARGET_SR,
        mono=True
    )

    if len(audio) == 0:
        raise ValueError("Audio file contains no audio.")

    # Convert NumPy audio to PyTorch tensor
    waveform = torch.tensor(
        audio,
        dtype=torch.float32
    ).unsqueeze(0)

    # Generate speaker embedding
    with torch.no_grad():
        embedding = model.encode_batch(waveform)

    # Remove unnecessary dimensions
    embedding = embedding.squeeze().cpu().numpy()

    # Normalize embedding
    norm = np.linalg.norm(embedding)

    if norm > 0:
        embedding = embedding / norm

    return embedding.astype(np.float32)


if __name__ == "__main__":
    audio_file = "audio/genuine_fixed.wav"

    embedding = extract_embedding(audio_file)

    print("ECAPA embedding extracted successfully!")
    print("Embedding shape:", embedding.shape)
    print("Embedding length:", len(embedding))
    print("First 10 values:")
    print(embedding[:10])