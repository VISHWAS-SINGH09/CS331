"""
VeriSupport — Decision Engine Service (Microservice)

This microservice handles trust score calculation and decision routing for the
VeriSupport platform. It runs as an independent service, consuming forensic
and AI scores from a message queue, computing the weighted trust score, and
routing the appropriate decision (auto-refund, manual review, or fraud alert).

Components:
    - ScoreWeights: Configuration for weighted ensemble
    - TrustScoreCalculator: T = w1(S_meta) + w2(S_ela) + w3(S_ai)
    - DecisionRouter: Routes decisions based on score thresholds
    - RefundAPI: Mock external banking API
    - NotificationService: Mock multi-channel notification delivery

Author: VeriSupport Team
Assignment: 5 — CS 331 Software Engineering Lab
"""

import json
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, Dict, List
from enum import Enum
from datetime import datetime


# ────────────────────────────────────────────────────────────────────
# Enums & Data Classes
# ────────────────────────────────────────────────────────────────────

class DecisionType(Enum):
    AUTO_REFUND = "auto_refund"
    MANUAL_REVIEW = "manual_review"
    FRAUD_ALERT = "fraud_alert"


class RefundStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"


@dataclass
class ScoreWeights:
    """
    Configuration for weighted trust score calculation.

    Default weights (empirically tuned):
      - Metadata: 20% (binary check)
      - ELA:      35% (compression artifact analysis)
      - AI:       45% (semantic understanding)
    """
    metadata_weight: float = 0.20
    ela_weight: float = 0.35
    ai_weight: float = 0.45

    def validate(self) -> bool:
        total = self.metadata_weight + self.ela_weight + self.ai_weight
        all_positive = all(w >= 0 for w in [
            self.metadata_weight, self.ela_weight, self.ai_weight
        ])
        return abs(total - 1.0) < 0.001 and all_positive


@dataclass
class TrustScoreResult:
    """Result of trust score calculation."""
    trust_score: float
    decision: str              # DecisionType value
    component_scores: Dict[str, float]
    weights_used: Dict[str, float]
    confidence_level: str      # "high", "medium", "low"
    timestamp: str


@dataclass
class FraudAlert:
    """Fraud alert for support agent review."""
    alert_id: str
    dispute_id: str
    trust_score: float
    flags: List[str]
    priority: str
    created_at: str
    evidence_summary: Dict


# ────────────────────────────────────────────────────────────────────
# TrustScoreCalculator
# ────────────────────────────────────────────────────────────────────

class TrustScoreCalculator:
    """
    Calculates trust scores using weighted ensemble algorithm.

    Formula: T = w1(S_meta) + w2(S_ela) + w3(S_ai)

    Where:
      - S_meta: Binary score (0 or 1) based on EXIF validity
      - S_ela:  Normalized score (0.0 - 1.0) from Error Level Analysis
      - S_ai:   Confidence score (0.0 - 1.0) from Vision-Language Model
    """

    DEFAULT_AUTO_REFUND_THRESHOLD = 0.9
    DEFAULT_FRAUD_ALERT_THRESHOLD = 0.5

    def __init__(
        self,
        weights: Optional[ScoreWeights] = None,
        auto_refund_threshold: float = DEFAULT_AUTO_REFUND_THRESHOLD,
        fraud_alert_threshold: float = DEFAULT_FRAUD_ALERT_THRESHOLD
    ):
        self._weights = weights or ScoreWeights()
        self._auto_refund_threshold = auto_refund_threshold
        self._fraud_alert_threshold = fraud_alert_threshold

        if not self._weights.validate():
            raise ValueError("Invalid weights: must be non-negative and sum to 1.0")

    @property
    def weights(self) -> ScoreWeights:
        return self._weights

    @property
    def auto_refund_threshold(self) -> float:
        return self._auto_refund_threshold

    @property
    def fraud_alert_threshold(self) -> float:
        return self._fraud_alert_threshold

    def calculate_trust_score(
        self,
        metadata_score: float,
        ela_score: float,
        ai_score: float
    ) -> TrustScoreResult:
        """Calculate the final trust score using weighted ensemble."""

        # Normalize scores to [0, 1]
        s_meta = max(0.0, min(1.0, metadata_score))
        s_ela = max(0.0, min(1.0, ela_score))
        s_ai = max(0.0, min(1.0, ai_score))

        # T = w1(S_meta) + w2(S_ela) + w3(S_ai)
        trust_score = (
            self._weights.metadata_weight * s_meta +
            self._weights.ela_weight * s_ela +
            self._weights.ai_weight * s_ai
        )
        trust_score = max(0.0, min(1.0, trust_score))

        # Decision based on thresholds
        decision = self.get_recommended_action(trust_score)

        # Confidence level
        scores = [s_meta, s_ela, s_ai]
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        if variance < 0.05:
            confidence = "high"
        elif variance < 0.15:
            confidence = "medium"
        else:
            confidence = "low"

        return TrustScoreResult(
            trust_score=trust_score,
            decision=decision.value,
            component_scores={"metadata": s_meta, "ela": s_ela, "ai": s_ai},
            weights_used={
                "metadata_weight": self._weights.metadata_weight,
                "ela_weight": self._weights.ela_weight,
                "ai_weight": self._weights.ai_weight
            },
            confidence_level=confidence,
            timestamp=datetime.now().isoformat()
        )

    def get_recommended_action(self, score: float) -> DecisionType:
        """Get recommended action based on trust score."""
        if score > self._auto_refund_threshold:
            return DecisionType.AUTO_REFUND
        elif score < self._fraud_alert_threshold:
            return DecisionType.FRAUD_ALERT
        else:
            return DecisionType.MANUAL_REVIEW


# ────────────────────────────────────────────────────────────────────
# RefundAPI (Mock External Service)
# ────────────────────────────────────────────────────────────────────

class RefundAPI:
    """Mock implementation of the external banking refund API."""

    def __init__(self):
        self._refund_count = 0

    def initiate_refund(self, transaction_id: str, amount: float) -> Tuple[bool, str]:
        """Initiate a refund request."""
        self._refund_count += 1
        refund_id = f"REF-{transaction_id[:8]}-{self._refund_count:04d}"
        print(f"    [RefundAPI] Initiating refund: {refund_id} for ${amount:.2f}")
        return (True, refund_id)

    def check_refund_status(self, refund_id: str) -> str:
        return RefundStatus.APPROVED.value


# ────────────────────────────────────────────────────────────────────
# NotificationService (Mock)
# ────────────────────────────────────────────────────────────────────

class NotificationService:
    """Mock multi-channel notification delivery (email, SMS, push)."""

    def __init__(self):
        self._sent_count = 0

    def send_email(self, to: str, subject: str, body: str) -> bool:
        self._sent_count += 1
        print(f"    [Email] To: {to} | Subject: {subject}")
        return True

    def send_sms(self, phone_number: str, message: str) -> bool:
        self._sent_count += 1
        print(f"    [SMS] To: {phone_number} | Message: {message[:50]}...")
        return True

    def send_push_notification(self, user_id: str, message: str) -> bool:
        self._sent_count += 1
        print(f"    [Push] To: {user_id} | Message: {message[:60]}...")
        return True


# ────────────────────────────────────────────────────────────────────
# DecisionRouter
# ────────────────────────────────────────────────────────────────────

class DecisionRouter:
    """
    Routes decisions based on trust scores and executes appropriate actions.

    Routes:
      - Score > 0.9   ->  Auto-refund via RefundAPI
      - Score < 0.5   ->  Fraud alert to support agent
      - 0.5 <= Score <= 0.9  ->  Manual review queue
    """

    def __init__(self):
        self._refund_api = RefundAPI()
        self._notification_service = NotificationService()
        self._routing_log: List[Dict] = []

    def route_decision(
        self,
        dispute_id: str,
        trust_result: TrustScoreResult,
        user_email: Optional[str] = None,
        order_amount: float = 0.0
    ) -> Dict:
        """Route the decision based on trust score result."""
        decision = trust_result.decision

        result = {
            "dispute_id": dispute_id,
            "decision": decision,
            "trust_score": trust_result.trust_score,
            "timestamp": datetime.now().isoformat(),
            "action_taken": None
        }

        if decision == DecisionType.AUTO_REFUND.value:
            success, refund_id = self._refund_api.initiate_refund(dispute_id, order_amount)
            result["action_taken"] = "auto_refund_processed" if success else "refund_failed"
            result["refund_id"] = refund_id
            if success and user_email:
                self._notification_service.send_email(
                    to=user_email,
                    subject="Your Refund Has Been Approved!",
                    body=f"Your refund for ${order_amount:.2f} has been processed."
                )

        elif decision == DecisionType.FRAUD_ALERT.value:
            alert = self._create_fraud_alert(dispute_id, trust_result)
            result["action_taken"] = "fraud_alert_created"
            result["alert_id"] = alert.alert_id
            result["alert_priority"] = alert.priority
            self._notification_service.send_push_notification(
                user_id="duty_agent",
                message=f"[{alert.priority.upper()}] Fraud alert: {alert.alert_id}"
            )

        else:  # MANUAL_REVIEW
            result["action_taken"] = "queued_for_manual_review"
            self._notification_service.send_push_notification(
                user_id="review_queue",
                message=f"New review: {dispute_id} (confidence: {trust_result.confidence_level})"
            )

        self._routing_log.append(result)
        return result

    def _create_fraud_alert(self, dispute_id: str, trust_result: TrustScoreResult) -> FraudAlert:
        """Create a fraud alert for support agent review."""
        if trust_result.trust_score < 0.2:
            priority = "high"
        elif trust_result.trust_score < 0.35:
            priority = "medium"
        else:
            priority = "low"

        flags = []
        scores = trust_result.component_scores
        if scores.get("metadata", 1) < 0.3:
            flags.append("SUSPICIOUS_METADATA")
        if scores.get("ela", 1) < 0.4:
            flags.append("IMAGE_MANIPULATION_DETECTED")
        if scores.get("ai", 1) < 0.5:
            flags.append("SEMANTIC_INCONSISTENCY")

        return FraudAlert(
            alert_id=f"ALERT-{dispute_id[:8]}-{datetime.now().strftime('%H%M%S')}",
            dispute_id=dispute_id,
            trust_score=trust_result.trust_score,
            flags=flags,
            priority=priority,
            created_at=datetime.now().isoformat(),
            evidence_summary=trust_result.component_scores
        )


# ────────────────────────────────────────────────────────────────────
# Decision Engine Service API
# ────────────────────────────────────────────────────────────────────

class DecisionEngineService:
    """
    Microservice wrapper around TrustScoreCalculator and DecisionRouter.

    In production, this would be a FastAPI app running on port 8004,
    consuming aggregated scores from decision_queue and publishing
    outcomes to notification_queue.
    """

    def __init__(self):
        self.calculator = TrustScoreCalculator()
        self.router = DecisionRouter()
        self.service_name = "decision-engine-service"
        self.port = 8004

    def health_check(self) -> Dict:
        """GET /health — Liveness probe."""
        return {"status": "healthy", "service": self.service_name, "port": self.port}

    def process_scores(
        self,
        dispute_id: str,
        metadata_score: float,
        ela_score: float,
        ai_score: float,
        user_email: Optional[str] = None,
        order_amount: float = 0.0
    ) -> Dict:
        """
        POST /process — Main decision endpoint.

        Consumes forensic + AI scores, calculates trust score, routes decision.
        """
        print(f"  [{self.service_name}] Processing scores for dispute: {dispute_id}")

        # Calculate trust score
        trust_result = self.calculator.calculate_trust_score(
            metadata_score, ela_score, ai_score
        )

        print(f"  [{self.service_name}] Trust Score Calculation:")
        print(f"    T = {self.calculator.weights.metadata_weight}*{trust_result.component_scores['metadata']:.2f}"
              f" + {self.calculator.weights.ela_weight}*{trust_result.component_scores['ela']:.2f}"
              f" + {self.calculator.weights.ai_weight}*{trust_result.component_scores['ai']:.2f}"
              f" = {trust_result.trust_score:.4f}")
        print(f"    Decision: {trust_result.decision}")
        print(f"    Confidence: {trust_result.confidence_level}")

        # Route decision
        route_result = self.router.route_decision(
            dispute_id=dispute_id,
            trust_result=trust_result,
            user_email=user_email,
            order_amount=order_amount
        )

        return {
            "service": self.service_name,
            "dispute_id": dispute_id,
            "trust_score": trust_result.trust_score,
            "decision": trust_result.decision,
            "confidence": trust_result.confidence_level,
            "component_scores": trust_result.component_scores,
            "action_taken": route_result["action_taken"],
            "timestamp": trust_result.timestamp
        }


# ────────────────────────────────────────────────────────────────────
# Standalone Demo
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("  VeriSupport — Decision Engine Service (Microservice)")

    service = DecisionEngineService()
    health = service.health_check()
    print(f"\n  Health Check: {health}")

    # Test scenarios
    scenarios = [
        ("Authentic",   1.0, 0.95, 0.92, "user@example.com", 49.99),
        ("Fraudulent",  0.0, 0.30, 0.25, "fraud@example.com", 199.99),
        ("Borderline",  0.0, 0.72, 0.65, "edge@example.com", 29.99),
    ]

    for name, s_meta, s_ela, s_ai, email, amount in scenarios:
        print(f"\n{'─' * 65}")
        print(f"  Scenario: {name}")
        print(f"  Inputs: S_meta={s_meta}, S_ela={s_ela}, S_ai={s_ai}")
        print(f"{'─' * 65}")

        result = service.process_scores(
            dispute_id=f"DISP-{name.upper()[:4]}-001",
            metadata_score=s_meta,
            ela_score=s_ela,
            ai_score=s_ai,
            user_email=email,
            order_amount=amount
        )
        print(f"  Result: {result['action_taken']}")

    print("\n  Service module loaded successfully!")
