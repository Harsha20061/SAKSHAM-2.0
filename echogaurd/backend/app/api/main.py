from fastapi import APIRouter
from app.api.routes import health, analysis, auth, contacts, calls, risk_events, websocket

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(risk_events.router, prefix="/calls", tags=["risk-events"])
api_router.include_router(websocket.router, tags=["websocket"])
