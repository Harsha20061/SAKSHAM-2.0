# Saksham 2.0

Saksham 2.0 (EchoGuard) is an academic prototype for real-time voice
impersonation protection. It combines synthetic-voice detection, trusted
speaker verification, speech-to-text, scam analysis, and risk scoring in a
browser-based WebRTC call experience.

This is a controlled browser/WebRTC prototype. It does not intercept arbitrary
GSM or cellular calls.

## Architecture

```text
Browser A ───── WebRTC peer audio ───── Browser B
    │                                      │
    └──────── signaling WebSocket ─────────┘
                                           │
                             analysis audio WebSocket
                                           │
                                  FastAPI backend
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
                  AASIST         ECAPA        Whisper + scam
                     └─────────────┼─────────────┘
                                   ▼
                              risk engine
                                   ▼
                         PostgreSQL/Supabase or SQLite
```

## Technology stack

- Python, FastAPI, Uvicorn, SQLAlchemy, Pydantic
- React, TypeScript, Vite, Tailwind CSS
- WebRTC and WebSockets
- AASIST/ONNX, ECAPA/SpeechBrain, faster-whisper
- SQLite for local development or PostgreSQL/Supabase for shared environments

## Prerequisites

- Windows 10/11
- Python 3.10 or newer (3.11-3.13 is recommended for ML package wheel
  compatibility)
- Node.js and npm
- Git
- A browser with microphone and WebRTC support
- The sibling `VoiceSecurity` directory and its model files for the full AI
  pipeline

Expected layout:

```text
SAKSHAM 2.0\
├── echogaurd\
└── VoiceSecurity\
```

## Backend setup (Windows)

```powershell
cd "C:\path\to\SAKSHAM 2.0\echogaurd\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The example configuration uses a local SQLite database and needs no database
server. For PostgreSQL/Supabase, edit `backend\.env`:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/echoguard
```

Never commit `.env`. Use a long, unique `JWT_SECRET_KEY`. `VOICE_SECURITY_PATH`
is optional and defaults to the sibling `VoiceSecurity` directory.

## Frontend setup

```powershell
cd "C:\path\to\SAKSHAM 2.0\echogaurd\frontend"
Copy-Item .env.example .env
npm ci
```

The frontend environment is:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000
```

## Model files

The full AI pipeline expects:

```text
VoiceSecurity\models\aasist\aasist.onnx
VoiceSecurity\models\ecapa\embedding_model.ckpt
VoiceSecurity\models\ecapa\classifier.ckpt
VoiceSecurity\models\ecapa\label_encoder.ckpt
VoiceSecurity\models\ecapa\mean_var_norm_emb.ckpt
```

The first faster-whisper warm-up may download the `tiny` model into the local
machine's cache. Model files and voice embeddings are sensitive; do not commit
credentials, raw audio, or personal biometric data.

## Verify setup

From the repository root:

```powershell
python scripts\verify_setup.py
```

This checks directories, dependency imports, environment-file presence,
frontend lockfiles, and required model paths without printing secret values.

## Run the complete application

Terminal 1, backend:

```powershell
cd "C:\path\to\SAKSHAM 2.0\echogaurd\backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2, frontend:

```powershell
cd "C:\path\to\SAKSHAM 2.0\echogaurd\frontend"
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`. API documentation is at
`http://localhost:8000/docs`, and the health endpoint is
`http://localhost:8000/api/health`.

## Tests and build

```powershell
cd "C:\path\to\SAKSHAM 2.0\echogaurd\backend"
.\.venv\Scripts\Activate.ps1
python -m pytest
```

```powershell
cd "C:\path\to\SAKSHAM 2.0\echogaurd\frontend"
npm run lint
npm run build
```

## Two-browser demo flow

1. Start the backend and frontend.
2. Open the frontend in two browser windows or profiles.
3. Create one account in each window.
4. Add the other account as a contact.
5. Start a call from one window and accept it in the other.
6. Grant microphone permission when prompted.
7. Confirm WebRTC and analysis status in the Call screen.
8. End the call and open the security report.

## Troubleshooting

- **Python or Node is not found:** install the prerequisites and reopen
  PowerShell.
- **PowerShell blocks activation:** run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- **Database connection refused:** use the SQLite value from `.env.example`, or
  start PostgreSQL and verify the complete `DATABASE_URL`.
- **Missing model:** place the files listed above in the sibling
  `VoiceSecurity\models` directories and run the verifier again.
- **Frontend cannot reach the backend:** confirm Uvicorn is on port 8000 and
  `VITE_API_BASE_URL` has the `/api` suffix.
- **WebSocket failure:** use `ws://localhost:8000` locally and keep the
  backend running.
- **CORS errors:** use the documented Vite URL or add the exact origin to the
  backend CORS configuration.
- **Microphone unavailable:** grant browser permission and use HTTPS or
  localhost.
- **Port already in use:** stop the process using port 8000/5173 or choose
  another port and update the frontend environment.
- **Slow first startup:** model loading and faster-whisper warm-up are expected
  during the first backend startup.

## Privacy and limitations

Audio chunks are processed for analysis and temporary files may be used during
model inference; the prototype does not intentionally provide permanent raw
audio storage. Speaker embeddings are sensitive biometric representations and
must be protected like other personal data. Detection and similarity scores are
risk signals, not guarantees of authenticity or identity.

The project is intended for academic/prototype use, not production deployment.
It does not claim perfect detection, universal language support, or guaranteed
scam detection.

See [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md) for release validation and
[ECHOGUARD_CONTEXT_CURRENT.md](./ECHOGUARD_CONTEXT_CURRENT.md) for architecture
notes.
