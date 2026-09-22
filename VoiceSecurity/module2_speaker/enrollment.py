import os
import json
import numpy as np

from module2_speaker.embedding import extract_embedding


DATABASE_DIR = "models/speaker_database"


def enroll_speaker(contact_id, audio_file):
    """
    Enroll a person's voice and store their voice embedding.
    """

    if not os.path.exists(audio_file):
        raise FileNotFoundError(
            f"Audio file not found: {audio_file}"
        )

    # Create database directory
    os.makedirs(DATABASE_DIR, exist_ok=True)

    # Extract voice embedding
    embedding = extract_embedding(audio_file)

    # Save embedding
    embedding_file = os.path.join(
        DATABASE_DIR,
        f"{contact_id}.npy"
    )

    np.save(embedding_file, embedding)

    # Save metadata
    metadata = {
        "contact_id": contact_id,
        "embedding_file": embedding_file,
        "embedding_size": len(embedding)
    }

    metadata_file = os.path.join(
        DATABASE_DIR,
        f"{contact_id}.json"
    )

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    return metadata


if __name__ == "__main__":

    contact_id = "abhinay"

    audio_file = "audio/genuine_fixed.wav"

    result = enroll_speaker(
        contact_id,
        audio_file
    )

    print("\nSpeaker enrolled successfully!")
    print(json.dumps(result, indent=2))