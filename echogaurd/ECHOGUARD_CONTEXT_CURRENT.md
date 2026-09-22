# EchoGuard — Project Context
## SIH 2026 | SIH26104 — AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks

> **Last updated:** 09 September 2026
> **Current milestone:** Real-time audio decoding and model-ready PCM pipeline verified live.

---

# 1. Project Identity

**Project:** EchoGuard
**Problem Statement:** SIH26104 — AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks

### Core positioning

EchoGuard is a **real-time voice trust and scam-prevention system**.

Instead of relying on a single deepfake detector, it combines:

1. **Voice authenticity / spoof detection**
2. **Trusted-speaker similarity**
3. **Conversational scam / social-engineering analysis**

These signals are fused by a Risk Engine and used to warn/intervene with the user.

### Core story

```text
CALL
  ↓
DETECT
  ↓
VERIFY
  ↓
ASSESS
  ↓
RISK
  ↓
EXPLAIN
  ↓
INTERVENE
  ↓
REPORT
```

---

# 2. Three-Level Detection Architecture

## Level 1 — DETECT

Detect whether the incoming voice is potentially synthetic / spoofed.

Output:

```json
{
  "spoof_probability": 0.92,
  "model_version": "model-name",
  "latency_ms": 120
}
```

## Level 2 — VERIFY

Compare the caller's voice characteristics against a trusted speaker profile.

Output:

```json
{
  "speaker_similarity": 0.21,
  "latency_ms": 180
}
```

Speaker similarity is a **risk signal**, not cryptographic identity proof.

## Level 3 — ASSESS

Use ASR followed by scam/social-engineering analysis.

Output:

```json
{
  "scam_score": 0.88,
  "indicators": [
    "money_request",
    "urgency"
  ],
  "transcript": "..."
}
```

Level 3 depends on ASR. These layers are complementary, not three independent parallel detectors.

---

# 3. Risk Engine

Current prototype formula:

```text
speaker_risk = 1 - speaker_similarity

risk =
    0.40 * spoof_probability
  + 0.30 * speaker_risk
  + 0.30 * scam_score
```

Thresholds:

```text
risk < 0.40       → LOW
0.40–<0.70       → SUSPICIOUS
risk >= 0.70     → HIGH
```

These weights and thresholds are **prototype parameters**, not scientifically validated universal thresholds.

### Example

```text
spoof_probability  = 0.92
speaker_similarity = 0.21
scam_score         = 0.88

risk_score ≈ 0.87
risk_level = HIGH
```

### Important integration decision

**Abdul's real Risk Engine is NOT integrated yet.**

Current sequence:

```text
Backend/audio pipeline
        ↓
Real AI models
        ↓
Live AI validation
        ↓
Integrate Abdul's Risk Engine
        ↓
Final end-to-end testing
```

Until then, keep the temporary/mock Risk Service.

---

# 4. Target Architecture

```text
                 CONTROLLED VoIP CALL
                         │
                         ▼
                 React Web UI
                         │
                    WebRTC Audio
                         │
                         ▼
                      WebSocket
                         │
                         ▼
                    FastAPI Gateway
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Level 1         Level 2          ASR
       Spoof           Speaker            │
       Detect          Verify             ▼
                                      Level 3
                                      Scam NLP
          └──────────────┬──────────────┘
                         ▼
                    Risk Engine
                         │
                 ┌───────┴───────┐
                 ▼               ▼
            Intervention     PostgreSQL
                                / Supabase
                                   │
                                   ▼
                            React SOC Dashboard
```

---

# 5. Calling Architecture

EchoGuard currently uses a **controlled browser-based VoIP/WebRTC prototype**.

It is NOT arbitrary cellular-call interception.

Production cellular integration would require authorized SIP/IMS/telecom/TSP media integration.

## Media architecture

Do NOT send the entire WebRTC call through FastAPI.

Current design:

```text
Browser A ←──── WebRTC P2P audio ────→ Browser B
```

Separate analysis stream:

```text
Browser B
   ├── WebRTC → remote caller audio
   │
   └── analysis audio
          ↓
       WebSocket
          ↓
       FastAPI
```

This keeps the actual call media path separate from the AI analysis transport.

---

# 6. Current Real-Time Audio Pipeline

## Verified live

```text
WebRTC Call
    ↓
Remote Audio
    ↓
MediaRecorder
    ↓
WebM / Opus Audio Chunks
    ↓
Analysis WebSocket
    ↓
FastAPI
    ↓
Compressed Audio Buffer
    ↓
PyAV Decoder
    ↓
16 kHz Mono int16 PCM
    ↓
10-second Rolling PCM Buffer
    ↓
Mock AI Analysis
    ↓
Risk UI
```

## Live verification results

The receiver browser showed:

```text
[WebRTC] Remote audio received
[WebRTC] Connection state: connected
```

Analysis transport showed:

```text
[Analysis WS] Sent audio chunk: 16439 bytes
[Analysis WS] Audio chunk received by backend
```

Backend state reached approximately:

```text
total_audio_bytes: 1332623
buffer_size_bytes: 1332623
pcm_buffer_seconds: 10
```

The frontend continued receiving analysis results such as:

```text
spoof_probability: 0.92
speaker_similarity: 0.21
scam_score: 0.88
risk_score: 0.87
```

These values are **mock/demo values**, not measured AI predictions.

### Current milestone

> **REAL-TIME AUDIO → MODEL-READY PCM PIPELINE: VERIFIED**

---

# 7. Audio Decoder

File:

```text
backend/app/services/audio_decoder.py
```

Purpose:

- Decode browser WebM/Opus or other supported container audio
- Convert to:
  - 16 kHz
  - mono
  - signed 16-bit PCM
- Return NumPy `int16` array

Key constants:

```python
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNEL_LAYOUT = "mono"
TARGET_SAMPLE_FORMAT = "s16"
```

Main function:

```python
decode_audio_to_pcm(audio_bytes: bytes) -> Optional[np.ndarray]
```

Duration helper:

```python
pcm_duration_seconds(pcm: np.ndarray) -> float
```

PyAV automatically handles supported container formats.

If the currently accumulated compressed stream is not yet decodable, the decoder returns `None` and waits for more audio.

---

# 8. Rolling Audio Buffer

File:

```text
backend/app/services/audio_buffer.py
```

Purpose:

Maintain model-ready audio in a rolling window.

Current configuration:

```text
Sample rate: 16,000 Hz
Channels:    mono
Format:      int16 PCM
Window:      10 seconds
```

Implementation:

```python
class RollingAudioBuffer:
    ...
```

The buffer always keeps the latest 10 seconds.

Important methods:

```python
append(pcm)
get_audio()
duration_seconds()
clear()
```

---

# 9. Current Backend Audio Processing

File:

```text
backend/app/api/routes/analysis.py
```

Current WebSocket processing:

```text
audio_chunk received
       ↓
Base64 decode
       ↓
Compressed audio buffer
       ↓
Every 3 chunks:
       ↓
PyAV decode
       ↓
16 kHz mono PCM
       ↓
RollingAudioBuffer
       ↓
Duration / buffer information
       ↓
Mock analysis result
```

Current prototype intentionally decodes the accumulated compressed buffer repeatedly.

This is acceptable for proving the pipeline.

### Future optimization

Do not immediately modify this now.

Later, replace repeated whole-buffer decoding with a more efficient incremental/streaming decoder or client-side PCM capture using an AudioWorklet.

---

# 10. Frontend

## Stack

```text
React
TypeScript
Vite
Tailwind CSS
Axios
Lucide React
React Router
WebRTC
WebSocket
```

Node environment:

```text
Node.js v24.18.0
npm 11.16.0
```

## Current frontend structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Topbar.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── call/
│   │   │   ├── AnalysisMetric.tsx
│   │   │   ├── AnalysisPanel.tsx
│   │   │   ├── IndicatorList.tsx
│   │   │   └── RiskBadge.tsx
│   │   └── pages/
│   │       ├── Dashboard.tsx
│   │       ├── Contacts.tsx
│   │       ├── Call.tsx
│   │       ├── Threats.tsx
│   │       ├── Login.tsx
│   │       └── Signup.tsx
│   ├── hooks/
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── calls.ts
│   │   ├── contacts.ts
│   │   ├── websocket.ts
│   │   ├── analysisWebSocket.ts
│   │   └── webrtc.ts
│   ├── types/
│   ├── lib/
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── package.json
├── vite.config.ts
└── ...
```

---

# 11. Frontend WebRTC

File:

```text
frontend/src/services/webrtc.ts
```

Current WebRTC configuration uses:

```text
STUN:
stun:stun.l.google.com:19302
```

The service supports:

```text
addLocalStream()
createOffer()
createAnswer()
setRemoteDescription()
addIceCandidate()
getConnectionState()
close()
```

Remote audio is attached to an HTML audio element.

---

# 12. Frontend Analysis WebSocket

File:

```text
frontend/src/services/analysisWebSocket.ts
```

Responsibilities:

- Connect to analysis WebSocket
- Start/stop analysis
- Capture remote audio
- Use `MediaRecorder`
- Encode chunks as Base64
- Send chunks every ~1 second
- Receive analysis results

Supported MIME types are checked dynamically, including:

```text
audio/webm;codecs=opus
audio/webm
audio/ogg;codecs=opus
audio/ogg
```

Current transport:

```text
Remote MediaStream
      ↓
MediaRecorder
      ↓
~1 second audio chunks
      ↓
Base64
      ↓
Analysis WebSocket
```

---

# 13. Call Page

File:

```text
frontend/src/components/pages/Call.tsx
```

Current important refs include:

```tsx
localStreamRef
remoteAudioRef
remoteStreamRef
webRTCRef
signalingRef
analysisSocketRef
remoteDescriptionSetRef
pendingIceCandidatesRef
cleanedUpRef
isCallerRef
```

Remote audio handling:

```text
WebRTC onTrack
      ↓
remoteStreamRef
      ↓
audio element
      ↓
AnalysisSocket.startAudioCapture(remoteStream)
```

There is also race-condition handling so that audio capture starts whether:

- remote stream arrives first, or
- analysis WebSocket connects first.

The analysis panel is currently shown to the receiver.

---

# 14. Signaling

Frontend:

```text
frontend/src/services/websocket.ts
```

Backend:

```text
backend/app/api/routes/websocket.py
backend/app/services/signaling_service.py
backend/app/services/websocket_manager.py
```

Supported signaling messages include:

```text
call_offer
call_answer
ice_candidate
call_end
ping
pong
hello
hello_ack
error
```

Current call flow:

```text
Caller
  ↓
Create Call Session
  ↓
Signaling WebSocket
  ↓
Offer
  ↓
Receiver
  ↓
Answer
  ↓
ICE Candidates
  ↓
WebRTC Connected
  ↓
Remote Audio
```

---

# 15. Incoming Call UX

`AppLayout` currently polls:

```text
GET /api/calls?status=RINGING
```

approximately every 2 seconds.

The frontend filters calls where the authenticated user is the receiver.

Incoming call overlay provides:

```text
Accept
Reject
```

Accepting navigates to:

```text
/call/{callId}
```

Current improvement still possible later:

- Display caller display name instead of caller UUID.

---

# 16. Backend Stack

```text
Python
FastAPI
Pydantic
SQLAlchemy Async
PostgreSQL / Supabase
JWT
Argon2/password hashing
WebSocket
PyAV
NumPy
```

AI target stack:

```text
PyTorch
librosa / torchaudio
ASVspoof-compatible anti-spoof model
SpeechBrain / ECAPA-TDNN
Whisper / faster-whisper
Scam classifier / rules
```

---

# 17. Backend Structure

```text
backend/
├── .env
├── .env.example
├── Dockerfile
├── pytest.ini
├── requirements.txt
├── app/
│   ├── main.py
│   ├── __init__.py
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   ├── websocket.py
│   │   └── routes/
│   │       ├── analysis.py
│   │       ├── auth.py
│   │       ├── calls.py
│   │       ├── contacts.py
│   │       ├── health.py
│   │       ├── risk_events.py
│   │       ├── threats.py
│   │       └── websocket.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── call_session.py
│   │   │   ├── contact.py
│   │   │   ├── risk_event.py
│   │   │   ├── user.py
│   │   │   └── __init__.py
│   │   └── repositories/
│   │       ├── call_session_repository.py
│   │       ├── contact_repository.py
│   │       ├── risk_event_repository.py
│   │       ├── user_repository.py
│   │       └── __init__.py
│   ├── models/
│   │   └── schemas.py
│   └── services/
│       ├── ai_service.py
│       ├── auth_service.py
│       ├── call_service.py
│       ├── contact_service.py
│       ├── mock_analysis_service.py
│       ├── risk_event_service.py
│       ├── risk_service.py
│       ├── signaling_service.py
│       ├── audio_decoder.py
│       ├── audio_buffer.py
│       └── websocket_manager.py
└── tests/
    ├── test_ai_service.py
    ├── test_analysis.py
    ├── test_analysis_websocket.py
    ├── test_auth_dependencies.py
    ├── test_auth_routes.py
    ├── test_auth_service.py
    ├── test_call_routes.py
    ├── test_call_service.py
    ├── test_contact_routes.py
    ├── test_contact_service.py
    ├── test_database.py
    ├── test_health.py
    ├── test_models.py
    ├── test_repositories.py
    ├── test_risk_event_routes.py
    ├── test_risk_event_service.py
    ├── test_risk_service.py
    ├── test_schemas.py
    ├── test_signaling_service.py
    ├── test_websocket_manager.py
    ├── test_websocket_routes.py
    ├── test_audio_buffer.py
    └── __init__.py
```

---

# 18. Backend APIs / Contracts

## Analysis

```json
{
  "session_id": "call-001",
  "audio_chunk": null,
  "timestamp": "..."
}
```

## AI Analysis Result

```json
{
  "session_id": "call-001",
  "spoof_probability": 0.92,
  "speaker_similarity": 0.21,
  "scam_score": 0.88,
  "indicators": [
    "money_request",
    "urgency"
  ],
  "latency_ms": 640
}
```

## Final Analysis Result

```json
{
  "session_id": "call-001",
  "spoof_probability": 0.92,
  "speaker_similarity": 0.21,
  "scam_score": 0.88,
  "risk_score": 0.87,
  "risk_level": "HIGH",
  "indicators": [
    "money_request",
    "urgency"
  ],
  "latency_ms": 640
}
```

---

# 19. Authentication

Implemented:

```text
POST /api/auth/signup
POST /api/auth/login
GET  /api/auth/me
```

Authentication:

```text
JWT Bearer Token
```

Passwords:

```text
pwdlib recommended password hashing
```

User creation and login are connected to PostgreSQL/Supabase.

---

# 20. Database

Supabase PostgreSQL is configured.

Current decisions:

```text
Data API: OFF
Automatically expose new tables: OFF
Automatic RLS: ON
Connection: Session Pooler
Driver: postgresql+asyncpg
```

The Session Pooler is used for persistent backend traffic.

Current models:

```text
User
Contact
CallSession
RiskEvent
```

Repositories exist for each major model.

---

# 21. Call State / Backend

Call sessions support:

```text
RINGING
ACTIVE
ENDED
FAILED
```

The backend validates participants before allowing call/signaling operations.

---

# 22. Tests

Before audio decoder work:

```text
148 passed, 5 warnings
```

After adding audio decoder and rolling buffer:

```text
152 passed, 5 warnings
```

Current verified commands:

```powershell
python -m py_compile app\api\routes\analysis.py
```

Passed.

```powershell
python -c "from app.api.routes.analysis import router; print('analysis.py import OK')"
```

Output:

```text
analysis.py import OK
```

```powershell
pytest -q
```

Output:

```text
152 passed, 5 warnings
```

Warnings are known framework deprecations and are intentionally not being fixed before functionality stabilization.

---

# 23. Audio Dependencies

Installed in backend virtual environment:

```text
PyAV: 18.1.0
NumPy: 2.5.3
```

Installed with:

```powershell
pip install av numpy
```

Important cleanup still pending:

```text
Add av and numpy to backend/requirements.txt
```

Do this before final deployment/reproducibility.

---

# 24. Known Technical Caveats

## 24.1 Browser audio format

Current browser capture uses compressed MediaRecorder output such as:

```text
WebM/Opus
```

The backend decodes it using PyAV.

## 24.2 Decoder efficiency

Current prototype repeatedly decodes the growing compressed buffer.

This is not the final production implementation.

Later:

```text
Incremental decoder
OR
AudioWorklet → raw PCM
```

## 24.3 Raw audio storage

Do not store raw call audio by default.

Only retain audio if there is a clear consent, privacy, retention and security requirement.

## 24.4 Speaker embeddings

Speaker embeddings are sensitive biometric representations.

They should not be described as cryptographic identity proofs.

## 24.5 Detection claims

Do not claim:

```text
100% deepfake detection
100% identity verification
universal multilingual support
```

unless properly tested and measured.

---

# 25. Current Mock/Prototype Status

The UI currently displays a simulated high-risk result similar to:

```text
Voice Authenticity Risk: 92%
Speaker Mismatch Risk: 79%
Scam Risk: 88%
Overall Risk: HIGH
```

These values are for demonstration only.

The next milestone is to make these values originate from actual AI inference over the live PCM audio.

---

# 26. Team Ownership

## Harsha

Current responsibility:

```text
Backend
Frontend
WebRTC
Real-time audio transport
Integration
```

The user is taking over the frontend/WebRTC work originally assigned to Mahesh.

## Abhinay

Responsible for:

```text
AI Engine
Voice spoof/deepfake detection
Speaker verification
ASR/scam analysis as applicable
```

## Abdul

Responsible for:

```text
Risk Engine
Signal fusion
Risk score
Risk level
```

Abdul's real Risk Engine will be integrated only after the user's backend and real AI work is completed.

---

# 27. Abdul Risk Engine — Reference Implementation

Current independent implementation:

```python
import json

SPOOF_WEIGHT = 0.40
SPEAKER_WEIGHT = 0.30
SCAM_WEIGHT = 0.30

def calculate_risk(abhinay_result):
    spoof_probability = abhinay_result["spoof_probability"]
    speaker_similarity = abhinay_result["speaker_similarity"]
    scam_score = abhinay_result["scam_score"]

    if not 0 <= spoof_probability <= 1:
        raise ValueError("spoof_probability must be between 0 and 1")
    if not 0 <= speaker_similarity <= 1:
        raise ValueError("speaker_similarity must be between 0 and 1")
    if not 0 <= scam_score <= 1:
        raise ValueError("scam_score must be between 0 and 1")

    speaker_risk = 1 - speaker_similarity

    risk_score = (
        SPOOF_WEIGHT * spoof_probability
        + SPEAKER_WEIGHT * speaker_risk
        + SCAM_WEIGHT * scam_score
    )

    if risk_score < 0.40:
        risk_level = "LOW"
    elif risk_score < 0.70:
        risk_level = "SUSPICIOUS"
    else:
        risk_level = "HIGH"

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "signals": {
            "spoof_probability": spoof_probability,
            "speaker_similarity": speaker_similarity,
            "speaker_risk": round(speaker_risk, 2),
            "scam_score": scam_score
        }
    }

def risk_to_json(result):
    return json.dumps(result, indent=2)
```

---

# 28. Current Git / Project State

Repository:

```text
echogaurd/
├── .git/
├── .venv/
├── backend/
├── frontend/
└── ECHOGUARD_CONTEXT.md
```

Recommended `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
env/
.pytest_cache/
.env
.vscode/
.idea/
.DS_Store
Thumbs.db
```

Never commit:

```text
.env
JWT secrets
database credentials
API keys
private model credentials
```

---

# 29. Frontend Build Status

Production build has been verified successfully.

Example result:

```text
vite v8.2.2 building client environment for production...
✓ 1935 modules transformed.
dist/index.html                   0.45 kB
dist/assets/index-C3Fiin3b.css   26.65 kB
dist/assets/index-Cl5yk3Up.js   334.83 kB
✓ built in 1.29s
```

---

# 30. What NOT To Change Right Now

The following parts are currently working and should not be randomly rewritten:

```text
WebRTC connection
WebRTC remote audio handling
Signaling
Analysis WebSocket transport
MediaRecorder capture
Base64 audio transport
FastAPI audio receiving
PyAV decoding
10-second rolling PCM buffer
Existing tests
```

Do not fix framework warnings before functionality stabilization.

---

# 31. NEXT MILESTONE — REAL AI INFERENCE

Current:

```text
PCM → Mock Analysis
```

Target:

```text
PCM
 │
 ├──► Voice Spoof Detection
 │
 ├──► Speaker Verification
 │
 └──► ASR
        ↓
     Scam Detection
```

Then normalize the model outputs into:

```json
{
  "session_id": "...",
  "spoof_probability": 0.0,
  "speaker_similarity": 0.0,
  "scam_score": 0.0,
  "indicators": [],
  "latency_ms": 0
}
```

Recommended abstraction:

```python
async def analyze_audio(
    pcm_audio,
    session_id,
):
    ...
```

The backend should depend on this interface rather than on model-specific implementation details.

---

# 32. Recommended Next Sequence

```text
CURRENT
  ↓
Live PCM pipeline verified
  ↓
[1] Add av + numpy to requirements.txt
  ↓
[2] Receive Abhinay's AI model/code
  ↓
[3] Define exact AI input/output contract
  ↓
[4] Connect PCM rolling buffer to AI service
  ↓
[5] Run real spoof detection
  ↓
[6] Run speaker verification
  ↓
[7] Run ASR
  ↓
[8] Run scam analysis
  ↓
[9] Validate latency and accuracy behavior
  ↓
[10] Replace mock analysis
  ↓
[11] Integrate Abdul's Risk Engine
  ↓
[12] Store risk events
  ↓
[13] Final intervention UX
  ↓
[14] End-to-end SIH demo
```

---

# 33. SIH Demo Story

The final demonstration should show:

```text
1. Trusted contact calls
2. WebRTC connection established
3. EchoGuard starts live analysis
4. Voice audio is captured
5. Audio is converted to model-ready PCM
6. AI detects suspicious voice characteristics
7. Speaker verification shows mismatch
8. ASR identifies suspicious scam language
9. Risk Engine combines signals
10. HIGH RISK warning appears
11. User can verify / hang up / report
12. SOC dashboard records the threat
```

The key differentiator is:

> **EchoGuard does not ask only "Is this voice fake?" It asks "Should I trust this call?"**

---

# 34. Current Status Summary

| Component | Status |
|---|---|
| FastAPI backend | ✅ Complete |
| Pydantic contracts | ✅ Complete |
| Authentication | ✅ Complete |
| PostgreSQL/Supabase | ✅ Connected |
| Database models | ✅ Complete |
| Repositories | ✅ Complete |
| Contacts API | ✅ Complete |
| Call sessions | ✅ Complete |
| Risk Events API | ✅ Complete |
| WebSocket infrastructure | ✅ Complete |
| WebRTC signaling | ✅ Working |
| WebRTC calling | ✅ Working |
| Incoming call UX | ✅ Working |
| Analysis WebSocket | ✅ Working |
| Real-time audio transport | ✅ Verified |
| Audio decoder | ✅ Implemented |
| PCM conversion | ✅ Verified |
| 10-second rolling buffer | ✅ Verified |
| Mock analysis | ✅ Working |
| Real AI models | ⏳ Next |
| Abdul Risk Engine | ⏳ Later |
| Final intervention logic | ⏳ Later |
| Production optimization | ⏳ Later |
| Final SIH demo | ⏳ Later |

---

# 35. One-Line Current State

> **EchoGuard currently has a working browser-based WebRTC calling system where remote call audio is captured in real time, streamed through a WebSocket to FastAPI, decoded from WebM/Opus into 16 kHz mono PCM, maintained in a 10-second rolling buffer, and passed through the existing mock analysis/risk pipeline. The next major task is replacing the mock analysis with Abhinay's real AI models.**
