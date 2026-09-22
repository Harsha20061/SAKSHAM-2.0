import pytest
from pydantic import ValidationError
from app.models.schemas import RiskEvaluationRequest, RiskEvaluationResult
from app.services.risk_service import RiskService

def test_valid_request_produces_result():
    request = RiskEvaluationRequest(
        spoof_probability=0.1,
        speaker_similarity=0.9,
        scam_score=0.2
    )
    result = RiskService.evaluate(request)
    assert isinstance(result, RiskEvaluationResult)

def test_risk_score_is_between_0_and_1():
    request = RiskEvaluationRequest(
        spoof_probability=0.1,
        speaker_similarity=0.9,
        scam_score=0.2
    )
    result = RiskService.evaluate(request)
    assert 0.0 <= result.risk_score <= 1.0

def test_risk_level_is_valid():
    request = RiskEvaluationRequest(
        spoof_probability=0.1,
        speaker_similarity=0.9,
        scam_score=0.2
    )
    result = RiskService.evaluate(request)
    assert result.risk_level in ["LOW", "SUSPICIOUS", "HIGH"]

def test_expected_mock_result():
    request = RiskEvaluationRequest(
        spoof_probability=0.1,
        speaker_similarity=0.9,
        scam_score=0.2
    )
    result = RiskService.evaluate(request)
    assert result.risk_score == 0.13
    assert result.risk_level == "LOW"

def test_deterministic_output():
    request1 = RiskEvaluationRequest(
        spoof_probability=0.1,
        speaker_similarity=0.9,
        scam_score=0.2
    )
    request2 = RiskEvaluationRequest(
        spoof_probability=0.1,
        speaker_similarity=0.9,
        scam_score=0.2
    )
    result1 = RiskService.evaluate(request1)
    result2 = RiskService.evaluate(request2)
    assert result1.risk_score == result2.risk_score
    assert result1.risk_level == result2.risk_level

def test_invalid_input_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        RiskEvaluationRequest(
            spoof_probability=1.5,  # Invalid: > 1.0
            speaker_similarity=0.9,
            scam_score=0.2
        )
