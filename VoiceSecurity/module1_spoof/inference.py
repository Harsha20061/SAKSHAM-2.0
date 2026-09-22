import time
import json
import numpy as np
import onnxruntime as ort

from module1_spoof.preprocess import load_audio, create_segments

from pathlib import Path

MODEL_PATH = str(
    Path(__file__).resolve().parents[1]
    / "models"
    / "aasist"
    / "aasist.onnx"
)


class AASISTDetector:

    def __init__(self):
        print("Loading AASIST model...")

        self.session = ort.InferenceSession(
            MODEL_PATH,
            providers=["CPUExecutionProvider"]
        )

        print("AASIST model loaded successfully.")

    def predict(self, audio_file):

        start_time = time.perf_counter()

        # Load audio
        audio = load_audio(audio_file)

        # Create 4.04 second segments
        segments = create_segments(audio)

        # Create batch
        batch = np.stack(segments).astype(np.float32)

        # Run model
        logits = self.session.run(
            ["logits"],
            {"wav": batch}
        )[0]

        print("\nRAW AASIST LOGITS:")
        print(logits)

        # Convert logits to probabilities
        logits = logits - np.max(
            logits,
            axis=1,
            keepdims=True
        )

        exp_logits = np.exp(logits)

        probabilities = (
            exp_logits /
            np.sum(exp_logits, axis=1, keepdims=True)
        )

        # AASIST output mapping:
        # class 0 = bona-fide
        # class 1 = spoof
        bona_fide_scores = probabilities[:, 0]
        spoof_scores = probabilities[:, 1]

        # Aggregate all segments
        spoof_probability = float(
            np.mean(spoof_scores)
        )

        latency_ms = int(
            (time.perf_counter() - start_time) * 1000
        )

        return {
            "spoof_probability": round(
                spoof_probability,
                4
            ),
            "segments_analyzed": len(segments),
            "segment_scores": [
                round(float(x), 4)
                for x in spoof_scores
            ],
            "latency_ms": latency_ms
        }


if __name__ == "__main__":

    audio_file = "audio/test.wav"

    detector = AASISTDetector()

    result = detector.predict(audio_file)

    print("\nFinal Module 1 result:")
    print(
        json.dumps(
            result,
            indent=2
        )
    )