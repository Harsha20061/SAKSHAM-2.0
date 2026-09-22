import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models.schemas import (
    AnalysisRequest,
    AIAnalysisResult,
    RiskEvaluationRequest,
    RiskEvaluationResult,
    FinalAnalysisResult
)

def test_valid_analysis_request():
    req = AnalysisRequest(session_id="123", audio_chunk="abcd", timestamp=datetime.now())
    assert req.session_id == "123"
    assert req.audio_chunk == "abcd"

def test_valid_ai_analysis_result():
    res = AIAnalysisResult(
        session_id="123",
        spoof_probability=0.5,
        speaker_similarity=0.8,
        scam_score=0.1,
        indicators=["urgency"],
        latency_ms=150.5
    )
    assert res.session_id == "123"
    assert res.spoof_probability == 0.5

def test_valid_risk_evaluation_request():
    req = RiskEvaluationRequest(spoof_probability=0.5, speaker_similarity=0.8, scam_score=0.1)
    assert req.spoof_probability == 0.5

def test_valid_risk_evaluation_result():
    res = RiskEvaluationResult(risk_score=0.9, risk_level="HIGH")
    assert res.risk_score == 0.9
    assert res.risk_level == "HIGH"

def test_valid_final_analysis_result():
    res = FinalAnalysisResult(
        session_id="123",
        spoof_probability=0.5,
        speaker_similarity=0.8,
        scam_score=0.1,
        risk_score=0.9,
        risk_level="HIGH",
        indicators=["urgency"],
        latency_ms=150.5
    )
    assert res.session_id == "123"

def test_probability_below_0():
    with pytest.raises(ValidationError):
        AIAnalysisResult(
            session_id="123",
            spoof_probability=-0.1,
            speaker_similarity=0.8,
            scam_score=0.1,
            indicators=[],
            latency_ms=100
        )

def test_probability_above_1():
    with pytest.raises(ValidationError):
        AIAnalysisResult(
            session_id="123",
            spoof_probability=1.1,
            speaker_similarity=0.8,
            scam_score=0.1,
            indicators=[],
            latency_ms=100
        )

def test_negative_latency():
    with pytest.raises(ValidationError):
        AIAnalysisResult(
            session_id="123",
            spoof_probability=0.5,
            speaker_similarity=0.8,
            scam_score=0.1,
            indicators=[],
            latency_ms=-10
        )

def test_risk_score_outside_0_1():
    with pytest.raises(ValidationError):
        RiskEvaluationResult(risk_score=1.5, risk_level="HIGH")
    with pytest.raises(ValidationError):
        RiskEvaluationResult(risk_score=-0.5, risk_level="HIGH")

def test_invalid_risk_level():
    with pytest.raises(ValidationError):
        RiskEvaluationResult(risk_score=0.5, risk_level="MEDIUM") # type: ignore
