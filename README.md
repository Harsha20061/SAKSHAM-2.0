# Saksham 2.0

## AI-Powered Real-Time Voice Impersonation Protection

Saksham 2.0 is an academic/prototype system that combines synthetic-voice
detection, trusted-speaker verification, speech-to-text, scam analysis, risk
scoring, and post-call security reporting in a browser-based call experience.

> Saksham 2.0 currently operates on controlled browser/WebRTC calls. It does
> not intercept arbitrary GSM, cellular, or native phone calls.

## Table of Contents

- [Overview](#overview)
- [Problem](#problem)
- [Solution](#solution)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [AI Pipeline](#ai-pipeline)
- [Risk Engine](#risk-engine)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Model Files](#model-files)
- [Verify Setup](#verify-setup)
- [Run the Application](#run-the-application)
- [Two-Browser Demo](#two-browser-demo)
- [Testing](#testing)
- [Performance](#performance)
- [Security and Privacy](#security-and-privacy)
- [Limitations](#limitations)
- [Project Status](#project-status)
- [Future Scope](#future-scope)
- [Troubleshooting](#troubleshooting)
- [Release Validation](#release-validation)
- [Academic / Prototype Disclaimer](#academic--prototype-disclaimer)

## Overview

Caller ID can identify an account or number, but it cannot establish that the
person speaking is genuine. Voice cloning, replayed audio, impersonation, and
social-engineering pressure can make a call appear trustworthy while
increasing the risk of financial or identity-related harm.

Saksham 2.0 uses multiple signals instead of relying on one detector. It
analyzes voice authenticity, compares the caller with an enrolled trusted
speaker profile when one exists, transcribes speech, detects scam indicators,
and presents a risk assessment with a post-call report.

## Problem

Modern impersonation attacks can combine a familiar identity with synthetic or
replayed speech and persuasive conversation tactics. A caller may sound like a
trusted person while requesting money, one-time passwords, secrecy, or urgent
action. These signals are probabilistic and can be affected by audio quality,
background noise, accents, and the available enrollment data.

## Solution

The prototype follows a defense-in-depth pipeline:

```text
CALL → DETECT → VERIFY → ASSESS → RISK → REPORT
```

- **Call:** Establish a controlled browser-to-browser WebRTC call.
- **Detect:** Estimate whether the audio has synthetic/spoof characteristics
  using AASIST.
- **Verify:** Compare the voice with an enrolled trusted speaker profile using
  ECAPA-TDNN embeddings when a profile is available.
- **Assess:** Transcribe speech with faster-whisper and analyze the transcript
  for scam and social-engineering indicators.
- **Risk:** Combine the available signals into prototype risk categories.
- **Report:** Persist risk events and provide a post-call security report.

## How It Works

```text
CALL
  |
  v
WebRTC Audio
  |
  +-------------------+
  |                   |
  v                   v
AASIST              ECAPA-TDNN
Spoof Detection     Speaker Verification
  |                   |
  +---------+---------+
            |
            v
      faster-whisper
            |
            v
       Scam Analysis
            |
            v
        Risk Engine
            |
      +-----+-----+
      |     |     |
     LOW SUSPICIOUS HIGH
            |
            v
     Security Report
```

## Architecture

```text
Browser A  <──────── WebRTC peer audio ────────>  Browser B
    |                                                |
    +──────────── signaling WebSocket ──────────────+
                                                     |
                                      analysis audio WebSocket
                                                     |
                                             FastAPI Backend
                                  ┌────────────┼────────────┐
                                  ▼            ▼            ▼
                              AI Services   Risk Engine  Database
                                  │                         │
                  AASIST / ECAPA / faster-whisper     SQLite or PostgreSQL
```

WebRTC carries the controlled call media between browsers. Separate signaling
and analysis WebSockets coordinate the call and send audio data to the
backend for processing. The backend exposes REST APIs for authentication,
contacts, calls, risk events, and security reports.

## AI Pipeline

### Module 1 — Synthetic Voice Detection

AASIST/ONNX analyzes audio for anti-spoofing signals. Its output is a
spoof-probability risk signal; it is not a universal guarantee that audio is
real or synthetic.

### Module 2 — Speaker Verification

ECAPA-TDNN generates speaker embeddings and compares an incoming voice with a
trusted profile. When no active profile is enrolled, the result is
`NOT_ENROLLED` and `speaker_similarity` remains null rather than being treated
as a speaker mismatch.

Speaker similarity is a probabilistic risk signal and is not cryptographic
proof of identity.

### Module 3 — Speech-to-Text and Scam Analysis

faster-whisper transcribes speech, with automatic language detection in the
current pipeline. Scam/social-engineering analysis then evaluates the
transcript for indicators such as urgency, money requests, OTP requests,
authority impersonation, and secrecy pressure. This stage depends on the
transcription output and can inherit ASR errors.

## Risk Engine

The current prototype formulation is:

```text
speaker_risk = 1 - speaker_similarity

risk =
    0.40 * spoof_probability
  + 0.30 * speaker_risk
  + 0.30 * scam_score
```

Prototype thresholds:

```text
0.00–0.39 → LOW
0.40–0.69 → SUSPICIOUS
0.70–1.00 → HIGH
```

These are prototype parameters, not universally validated security
thresholds. If no trusted speaker profile exists, the system does not
interpret that state as a mismatch; available signals are normalized instead.

## Key Features

- Browser-based WebRTC calling
- Signaling and real-time analysis over WebSockets
- AASIST anti-spoof analysis
- ECAPA-TDNN speaker verification and voice enrollment
- faster-whisper speech-to-text
- Scam/social-engineering indicator analysis
- Combined risk scoring and persisted risk events
- Authentication and contact management
- Post-call security reports
- SQLite local development support
- PostgreSQL/Supabase configuration support
- Light/dark theme support
- Automated backend tests
- Setup verification

## Technology Stack

| Area | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn, SQLAlchemy, Pydantic |
| Communication | WebRTC, WebSockets |
| AI | AASIST/ONNX, ECAPA/SpeechBrain, faster-whisper |
| Database | SQLite, PostgreSQL, Supabase-compatible PostgreSQL |
| Testing | Pytest |
| Containerization | Dockerfile |

## Repository Structure

```text
SAKSHAM 2.0/
├── README.md
├── echogaurd/
│   ├── backend/
│   ├── frontend/
│   ├── evaluation/
│   ├── scripts/
│   ├── RELEASE_CHECKLIST.md
│   └── ECHOGUARD_CONTEXT_CURRENT.md
└── VoiceSecurity/
```

- `echogaurd/backend/` contains the FastAPI application, services, database
  models/repositories, and tests.
- `echogaurd/frontend/` contains the React/Vite application.
- `echogaurd/evaluation/` contains diagnostic performance measurements.
- `echogaurd/scripts/verify_setup.py` checks local prerequisites and model
  paths.
- `VoiceSecurity/` contains the AI modules, model files, audio fixtures, and
  model-related runtime assets.

## Prerequisites

- Windows 10/11
- Python 3.10 or newer
- Python 3.11–3.13 recommended for machine-learning package compatibility
- Node.js and npm
- Git
- A modern browser with microphone and WebRTC support
- The sibling `VoiceSecurity` directory and its required model files for the
  complete AI pipeline

## Installation

Run these commands from the repository root in PowerShell.

### Backend

```powershell
Set-Location .\echogaurd\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Frontend

```powershell
Set-Location ..\frontend
Copy-Item .env.example .env
npm ci
```

## Configuration

The backend reads configuration from `echogaurd\backend\.env`. The example
uses SQLite for local development:

```env
DATABASE_URL=sqlite+aiosqlite:///./echoguard.db
JWT_SECRET_KEY=change_this_secret_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
VOICE_SECURITY_PATH=../../VoiceSecurity
```

For PostgreSQL/Supabase, replace the database value with your own connection
string:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/echoguard
```

Keep real credentials and secrets in `.env`, never commit that file, and use a
long unique `JWT_SECRET_KEY`. `VOICE_SECURITY_PATH` is optional; the backend
otherwise resolves the sibling `VoiceSecurity` directory from the project
layout.

## Frontend Environment

The frontend reads `echogaurd\frontend\.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000
```

The API URL must include the `/api` suffix.

## Model Files

The complete AI pipeline expects these files:

```text
VoiceSecurity/models/aasist/aasist.onnx
VoiceSecurity/models/ecapa/embedding_model.ckpt
VoiceSecurity/models/ecapa/classifier.ckpt
VoiceSecurity/models/ecapa/label_encoder.ckpt
VoiceSecurity/models/ecapa/mean_var_norm_emb.ckpt
```

The first faster-whisper warm-up may download its `tiny` model into the local
machine cache. Do not commit credentials, raw personal recordings, or
unapproved biometric data. Speaker embeddings are sensitive biometric
representations.

## Verify Setup

From the repository root:

```powershell
python echogaurd\scripts\verify_setup.py
```

The verifier checks the Python version, project directories, environment
configuration availability, frontend lockfile, required imports, and required
model paths without printing secret values.

## Run the Application

Open two PowerShell terminals from the repository root.

### Backend

```powershell
Set-Location .\echogaurd\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
Set-Location .\echogaurd\frontend
npm run dev
```

Open the frontend at `http://localhost:5173`.

| Service | URL |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/api/health` |

## Two-Browser Demo

1. Start the backend.
2. Start the frontend.
3. Open two browser windows or profiles.
4. Create an account in each window.
5. Add each account as a contact.
6. Start a call from one window.
7. Accept the incoming call in the other window.
8. Grant microphone permission.
9. Verify the WebRTC connection and analysis status.
10. Observe AASIST, ECAPA, and ASR/scam analysis status where available.
11. End the call.
12. Open the post-call security report.

This demo uses controlled browser media and does not intercept phone-network
calls.

## Testing

### Backend

```powershell
Set-Location .\echogaurd\backend
.\.venv\Scripts\Activate.ps1
python -m pytest
```

### Frontend

```powershell
Set-Location .\echogaurd\frontend
npm run lint
npm run build
```

## Performance

Diagnostic measurements are stored in:

- [baseline.csv](./echogaurd/evaluation/performance/baseline.csv)
- [optimized.csv](./echogaurd/evaluation/performance/optimized.csv)
- [performance_report.md](./echogaurd/evaluation/performance/performance_report.md)

The report describes a measured optimization in the tested CPU environment:
the observed median end-to-end diagnostic latency decreased from 5840.7 ms to
3879.9 ms across the reported samples. These are prototype measurements, not
production latency guarantees or browser-call SLAs.

## Security and Privacy

- Audio is processed for analysis, and temporary files may be used during
  model inference.
- The prototype does not intentionally provide permanent raw-audio storage.
- Speaker embeddings are sensitive biometric representations.
- Authentication tokens, database credentials, and JWT secrets must remain in
  local environment configuration.
- Database access must be protected with appropriate credentials and network
  controls in shared environments.
- Detection and similarity scores are risk signals, not guarantees of
  authenticity or identity.

## Limitations

- Controlled browser/WebRTC prototype; no arbitrary GSM, cellular, or native
  phone-call interception.
- Spoof detection and speaker similarity are probabilistic.
- ASR can produce transcription errors.
- Scam analysis can produce false positives and false negatives.
- Background noise, microphones, codecs, and acoustic conditions affect
  results.
- Language coverage and model behavior are limited by the configured models.
- Risk thresholds are prototype parameters, not validated universal controls.

## Project Status

- [x] React + TypeScript frontend
- [x] FastAPI backend
- [x] Authentication
- [x] Contact management
- [x] WebRTC calling
- [x] WebSocket signaling
- [x] Real-time analysis WebSocket
- [x] AASIST spoof analysis
- [x] ECAPA speaker verification
- [x] Speech-to-text
- [x] Scam analysis
- [x] Risk engine
- [x] Risk-event persistence
- [x] Post-call security reports
- [x] SQLite development support
- [x] PostgreSQL/Supabase configuration
- [x] Automated backend tests
- [x] Frontend lint/build
- [x] Setup verification

## Future Scope

- Authorized telecom/SIP/IMS media integration
- Lower-latency streaming inference
- Improved replay and deepfake defenses
- Larger evaluation datasets
- More robust multilingual evaluation
- Privacy-preserving speaker-profile storage
- Stronger scam and conversational-context analysis
- More extensive attack-condition testing

## Troubleshooting

- **Python or Node is not found:** Install the prerequisite and reopen
  PowerShell so PATH changes are loaded.
- **PowerShell blocks activation:** Run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- **Database connection refused:** Use the SQLite value from `.env.example`, or
  start PostgreSQL and verify the complete `DATABASE_URL`.
- **Missing model:** Place the files listed in [Model Files](#model-files) in
  the sibling `VoiceSecurity` directories and rerun the setup verifier.
- **Frontend cannot reach the backend:** Confirm Uvicorn is on port 8000 and
  `VITE_API_BASE_URL` includes `/api`.
- **WebSocket failure:** Use `ws://localhost:8000` locally and keep the
  backend running.
- **CORS errors:** Use the documented Vite URL or add the exact frontend
  origin to the backend CORS configuration.
- **Microphone unavailable:** Grant browser permission and use HTTPS or
  localhost.
- **Port already in use:** Stop the process using port 8000/5173 or select
  another port and update the frontend environment.
- **Slow first model startup:** AASIST, speaker components, and
  faster-whisper may require model initialization or local cache downloads.

## Release Validation

- [Release checklist](./echogaurd/RELEASE_CHECKLIST.md)
- [Current architecture context](./echogaurd/ECHOGUARD_CONTEXT_CURRENT.md)
- [Setup verifier](./echogaurd/scripts/verify_setup.py)

## Academic / Prototype Disclaimer

Saksham 2.0 is an academic/prototype system and should not be used as the
sole security control for high-risk financial, identity, emergency,
telecommunications, or other critical decisions without further validation.
It makes no claim of perfect detection, perfect speaker identification,
guaranteed scam detection, universal multilingual support, or production-ready
telecom interception.
