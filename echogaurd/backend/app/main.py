from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from app.db.database import init_db
import json
import asyncio

from app.core.config import settings
from app.api.main import api_router
from app.services.ai_service import ai_service

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")
@app.on_event("startup")
async def startup_event():
    await init_db()
    await asyncio.to_thread(ai_service.warmup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.websocket("/ws/analyze/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Mock AI processing
            await asyncio.sleep(0.5)
            response = {
                "session_id": session_id,
                "spoof_probability": 0.92,
                "speaker_similarity": 0.21,
                "scam_score": 0.88,
                "risk_score": 0.87,
                "risk_level": "HIGH",
                "indicators": ["money_request", "urgency", "otp_request"],
                "latency_ms": 640
            }
            await websocket.send_text(json.dumps(response))
    except Exception as e:
        print(f"WebSocket closed for {session_id}: {e}")

@app.post("/api/calls/start")
async def start_call():
    return {"message": "Call started"}

@app.post("/api/calls/end")
async def end_call():
    return {"message": "Call ended"}

@app.post("/api/enrollment")
async def enrollment():
    return {"message": "Enrolled"}


@app.get("/api/threats")
async def threats():
    return {"threats": []}

@app.post("/api/verification/request")
async def verification_request():
    return {"message": "Verification requested"}
