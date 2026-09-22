from typing import Optional

from app.models.schemas import (
    RiskEvaluationRequest,
    RiskEvaluationResult,
)


class RiskService:

    @staticmethod
    def calculate_risk(
        spoof_probability: float,
        speaker_similarity: Optional[float],
        scam_score: float,
    ) -> dict:

        if speaker_similarity is None:
            total_weight = 0.70
            risk_score = (
                (0.40 / total_weight) * spoof_probability
                + (0.30 / total_weight) * scam_score
            )
        else:
            speaker_risk = 1 - speaker_similarity
            risk_score = (
                0.40 * spoof_probability
                + 0.30 * speaker_risk
                + 0.30 * scam_score
            )

        if risk_score < 0.40:
            risk_level = "LOW"
        elif risk_score < 0.70:
            risk_level = "SUSPICIOUS"
        else:
            risk_level = "HIGH"

        return {
            "risk_score": round(
                risk_score,
                2,
            ),
            "risk_level": risk_level,
        }

    @staticmethod
    def evaluate(
        request: RiskEvaluationRequest,
    ) -> RiskEvaluationResult:
        """
        Evaluate the combined AI signals and return
        the final EchoGuard risk result.
        """

        result = RiskService.calculate_risk(
            spoof_probability=request.spoof_probability,
            speaker_similarity=request.speaker_similarity,
            scam_score=request.scam_score,
        )

        return RiskEvaluationResult(
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
        )