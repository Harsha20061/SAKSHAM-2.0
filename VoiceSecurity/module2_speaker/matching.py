from pathlib import Path

import numpy as np

from module2_speaker.embedding import extract_embedding


DATABASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "speaker_database"
)


def cosine_similarity(embedding1, embedding2):
    embedding1 = np.asarray(embedding1)
    embedding2 = np.asarray(embedding2)

    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = np.dot(
        embedding1,
        embedding2
    ) / (norm1 * norm2)

    similarity = np.clip(
        similarity,
        0.0,
        1.0
    )

    return float(similarity)


def compare_voice(audio_file, contact_id):
    embedding_file = (
        DATABASE_DIR / f"{contact_id}.npy"
    )

    if not embedding_file.exists():
        raise FileNotFoundError(
            f"No enrolled voice found for contact: {contact_id}"
        )

    stored_embedding = np.load(
        embedding_file
    )

    incoming_embedding = extract_embedding(
        audio_file
    )

    similarity = cosine_similarity(
        incoming_embedding,
        stored_embedding
    )

    return {
        "contact_id": contact_id,
        "speaker_similarity": round(
            similarity,
            4
        )
    }


if __name__ == "__main__":
    audio_file = "audio/genuine_fixed.wav"

    result = compare_voice(
        audio_file,
        "abhinay"
    )

    print("\nSpeaker verification result:")
    print(result)
