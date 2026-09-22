import pytest
from app.models.schemas import AnalysisRequest, AIAnalysisResult
from app.services.ai_service import ai_service

@pytest.mark.anyio
async def test_ai_service_analyze():
    req = AnalysisRequest(session_id="test_session_123")
    res = await ai_service.analyze(req)

    # 1. Valid AnalysisRequest produces AIAnalysisResult
    assert isinstance(res, AIAnalysisResult)
    assert res.session_id == "test_session_123"

    # 2. Output values are within valid ranges
    assert 0.0 <= res.spoof_probability <= 1.0
    assert 0.0 <= res.speaker_similarity <= 1.0
    assert 0.0 <= res.scam_score <= 1.0
    assert res.latency_ms >= 0.0

    # 3. Expected demo values are returned
    assert res.spoof_probability == 0.92
    assert res.speaker_similarity == 0.21
    assert res.scam_score == 0.88
    assert res.latency_ms == 640.0

    # 4. Indicators are returned correctly
    assert res.indicators == ["money_request", "urgency"]

    # 5. The service does not produce random output
    # By repeating the call, we verify deterministic output
    res2 = await ai_service.analyze(req)
    assert res.model_dump() == res2.model_dump()
