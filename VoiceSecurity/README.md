# VoiceSecurity

Project structure for the real-time voice integrity verification system.

## Modules
- module1_spoof: AI-generated / cloned voice detection
- module2_speaker: stored-contact speaker verification
- module3_scam: speech-to-text and scam/intent detection

## Initial workflow
1. Put test audio in `audio/`
2. Implement and test Module 1 first.
3. Implement Module 2 speaker enrollment and matching.
4. Implement Module 3 speech-to-text and threat detection.
5. Connect outputs in `main.py`.

Final output target:
{
  "spoof_probability": 0.92,
  "speaker_similarity": 0.21,
  "scam_score": 0.88,
  "indicators": ["money_request", "urgency", "otp_request"],
  "latency_ms": 640
}
