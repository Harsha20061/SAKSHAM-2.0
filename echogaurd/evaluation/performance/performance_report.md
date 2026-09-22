# Phase 2 Performance Report

## Scope

This report measures the existing CPU pipeline before and after one narrowly scoped optimization. No model, threshold, sample rate, WebSocket protocol, or risk semantics changed.

- Python: 3.14.6
- Interpreter: project `.venv`
- Audio: `VoiceSecurity/audio/scam_test_fixed.wav`
- Audio format: mono, 16 kHz, 16-bit PCM WAV
- Profile: no active speaker profile
- Runs: 3 per phase (one cold, two warm)
- p95/p99: maximum of the three observed samples; this is a small diagnostic sample, not a production load benchmark

## Summary

| Metric | Baseline p50 | Optimized p50 | Baseline p95 | Optimized p95 | Baseline p99 | Optimized p99 |
|---|---:|---:|---:|---:|---:|---:|
| First result / end-to-end (ms) | 5840.7 | 3879.9 | 13443.3 | 9422.6 | 13443.3 | 9422.6 |
| AASIST (ms) | 2756 | 1174 | 5582 | 3086 | 5582 | 3086 |
| ECAPA (ms) | 0 | 0 | 0 | 0 | 0 | 0 |
| ASR + scam (ms) | 3084 | 2705 | 7860 | 6336 | 7860 | 6336 |
| Risk Engine (ms) | 0 | 0 | 0 | 0 | 0 | 0 |

## Change

`module1_spoof.preprocess.load_audio` now reads an input WAV directly when it is already mono, 16 kHz, and 16-bit PCM. Other formats and WAV files requiring conversion continue through the existing FFmpeg path.

This removes duplicate FFmpeg conversion for backend-generated analysis WAV files while preserving the model input format.

## Quality comparison

The measured outputs were unchanged across all runs:

- AASIST spoof probability: `0.006`
- Scam score: `0.75`
- Detected language: `en`
- Scam indicators: `otp_request`, `urgency`, `authority_impersonation`, `secrecy_pressure`
- No-profile behavior: `speaker_similarity = null`, `NOT_ENROLLED`

## Interpretation

The optimization improved the observed median end-to-end latency by approximately 33.6% and reduced the observed cold run from 13.44 s to 9.42 s. ASR remains the dominant steady-state component. No claim is made about browser-call latency or production p95/p99 until a larger controlled benchmark and live call validation are available.
