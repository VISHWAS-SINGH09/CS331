"""
VeriSupport - Trust Score Calculator Module

This module implements the decision-making engine for VeriSupport:
- ScoreWeights: Configuration for weighted ensemble
- TrustScoreCalculator: Computes trust score using T = w₁(S_meta) + w₂(S_ela) + w₃(S_ai)
- DecisionRouter: Routes decisions based on score thresholds

Author: VeriSupport Team
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List, Callable
from enum import Enum
from datetime import datetime


class DecisionType(Enum):
    """Types of decisions the system can make."""
    AUTO_REFUND = "auto_refund"
    MANUAL_REVIEW = "manual_review"
    FRAUD_ALERT = "fraud_alert"


class RefundStatus(Enum):
    """Status of refund processing."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"


@dataclass
class ScoreWeights:
    """
    Configuration for weighted trust score calculation.
    
    Default weights based on empirical tuning:
    - Metadata: 20% (binary check)
    - ELA: 35% (compression artifact analysis)
    - AI: 45% (semantic understanding)
    """
    metadata_weight: float = 0.20
    ela_weight: float = 0.35
    ai_weight: float = 0.45
    
    def validate(self) -> bool:
        """
        Validate that weights sum to 1.0 and are non-negative.
        
        Returns:
            True if valid, False otherwise
        """
        total = self.metadata_weight + self.ela_weight + self.ai_weight
        all_positive = all(w >= 0 for w in [
            self.metadata_weight, 
            self.ela_weight, 
            self.ai_weight
        ])
        return abs(total - 1.0) < 0.001 and all_positive
    
    def to_dict(self) -> Dict[str, float]:
        """Convert weights to dictionary."""
        return {
            "metadata_weight": self.metadata_weight,
            "ela_weight": self.ela_weight,
            "ai_weight": self.ai_weight
        }


@dataclass
class TrustScoreResult:
    """Result of trust score calculation."""
    trust_score: float
    decision: DecisionType
    component_scores: Dict[str, float]
    weights_used: ScoreWeights
    calculation_timestamp: datetime
    confidence_level: str  # "high", "medium", "low"


@dataclass
class FraudAlert:
    """Fraud alert for support agent review."""
    alert_id: str
    dispute_id: str
    trust_score: float
    flags: List[str]
    priority: str  # "high", "medium", "low"
    created_at: datetime
    evidence_summary: Dict


class TrustScoreCalculator:
    """
    Calculates trust scores using weighted ensemble algorithm.
    
    Formula: T = w₁(S_meta) + w₂(S_ela) + w₃(S_ai)
    
    Where:
    - S_meta: Binary score (0 or 1) based on EXIF validity
    - S_ela: Normalized score (0.0 - 1.0) from Error Level Analysis
    - S_ai: Confidence score (0.0 - 1.0) from Vision-Language Model
    """
    
    # Default thresholds from project requirements
    DEFAULT_AUTO_REFUND_THRESHOLD = 0.9
    DEFAULT_FRAUD_ALERT_THRESHOLD = 0.5
    
    def __init__(
        self,
        weights: Optional[ScoreWeights] = None,
        auto_refund_threshold: float = DEFAULT_AUTO_REFUND_THRESHOLD,
        fraud_alert_threshold: float = DEFAULT_FRAUD_ALERT_THRESHOLD
    ):
        """
        Initialize the trust score calculator.
        
        Args:
            weights: Score weights configuration (default: balanced weights)
            auto_refund_threshold: Threshold for auto-refund (default: 0.9)
            fraud_alert_threshold: Threshold for fraud alert (default: 0.5)
        """
        self._weights = weights or ScoreWeights()
        self._auto_refund_threshold = auto_refund_threshold
        self._fraud_alert_threshold = fraud_alert_threshold
        self._calculation_count = 0
        
        # Validate weights
        if not self._weights.validate():
            raise ValueError("Invalid weights: must be non-negative and sum to 1.0")
    
    @property
    def weights(self) -> ScoreWeights:
        """Get current weights."""
        return self._weights
    
    @property
    def auto_refund_threshold(self) -> float:
        """Get auto-refund threshold."""
        return self._auto_refund_threshold
    
    @property
    def fraud_alert_threshold(self) -> float:
        """Get fraud alert threshold."""
        return self._fraud_alert_threshold
    
    def set_weights(self, w1: float, w2: float, w3: float) -> None:
        """
        Update the score weights.
        
        Args:
            w1: Metadata weight
            w2: ELA weight
            w3: AI weight
            
        Raises:
            ValueError: If weights don't sum to 1.0
        """
        new_weights = ScoreWeights(
            metadata_weight=w1,
            ela_weight=w2,
            ai_weight=w3
        )
        
        if not new_weights.validate():
            raise ValueError(f"Weights must sum to 1.0, got {w1 + w2 + w3}")
        
        self._weights = new_weights
    
    def set_thresholds(
        self, 
        auto_refund: float, 
        fraud_alert: float
    ) -> None:
        """
        Update decision thresholds.
        
        Args:
            auto_refund: New auto-refund threshold
            fraud_alert: New fraud alert threshold
            
        Raises:
            ValueError: If thresholds are invalid
        """
        if not (0 <= fraud_alert < auto_refund <= 1):
            raise ValueError(
                "Thresholds must satisfy: 0 <= fraud_alert < auto_refund <= 1"
            )
        
        self._auto_refund_threshold = auto_refund
        self._fraud_alert_threshold = fraud_alert
    
    def calculate_trust_score(
        self,
        metadata_score: float,
        ela_score: float,
        ai_score: float
    ) -> TrustScoreResult:
        """
        Calculate the final trust score using weighted ensemble.
        
        Args:
            metadata_score: Binary score (0 or 1) from metadata analysis
            ela_score: Normalized score (0.0 - 1.0) from ELA
            ai_score: Confidence score (0.0 - 1.0) from AI model
            
        Returns:
            TrustScoreResult with score, decision, and details
        """
        self._calculation_count += 1
        
        # Normalize scores to valid range
        scores = self._normalize_scores([metadata_score, ela_score, ai_score])
        s_meta, s_ela, s_ai = scores
        
        # Calculate weighted trust score
        # T = w₁(S_meta) + w₂(S_ela) + w₃(S_ai)
        trust_score = (
            self._weights.metadata_weight * s_meta +
            self._weights.ela_weight * s_ela +
            self._weights.ai_weight * s_ai
        )
        
        # Ensure trust score is in valid range
        trust_score = max(0.0, min(1.0, trust_score))
        
        # Determine decision based on thresholds
        decision = self.get_recommended_action(trust_score)
        
        # Calculate confidence level
        confidence = self._calculate_confidence(scores, trust_score)
        
        return TrustScoreResult(
            trust_score=trust_score,
            decision=decision,
            component_scores={
                "metadata": s_meta,
                "ela": s_ela,
                "ai": s_ai
            },
            weights_used=self._weights,
            calculation_timestamp=datetime.now(),
            confidence_level=confidence
        )
    
    def get_recommended_action(self, score: float) -> DecisionType:
        """
        Get recommended action based on trust score.
        
        Args:
            score: Trust score (0.0 - 1.0)
            
        Returns:
            Recommended DecisionType
        """
        if score > self._auto_refund_threshold:
            return DecisionType.AUTO_REFUND
        elif score < self._fraud_alert_threshold:
            return DecisionType.FRAUD_ALERT
        else:
            return DecisionType.MANUAL_REVIEW
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """
        Normalize scores to valid [0, 1] range.
        
        Args:
            scores: List of raw scores
            
        Returns:
            List of normalized scores
        """
        return [max(0.0, min(1.0, s)) for s in scores]
    
    def _calculate_confidence(
        self, 
        component_scores: List[float], 
        final_score: float
    ) -> str:
        """
        Calculate confidence level based on score agreement.
        
        Returns "high" if scores agree, "low" if they disagree significantly.
        """
        # Calculate variance in component scores
        mean_score = sum(component_scores) / len(component_scores)
        variance = sum((s - mean_score) ** 2 for s in component_scores) / len(component_scores)
        
        if variance < 0.05:
            return "high"
        elif variance < 0.15:
            return "medium"
        else:
            return "low"


class RefundAPI:
    """
    Interface for external refund API (mock implementation).
    
    In production, this would connect to the actual banking/payment API.
    """
    
    def __init__(self, api_endpoint: str = "https://api.refund.example.com"):
        """Initialize the refund API client."""
        self._api_endpoint = api_endpoint
        self._refund_count = 0
    
    def initiate_refund(
        self, 
        transaction_id: str, 
        amount: float
    ) -> Tuple[bool, str]:
        """
        Initiate a refund request.
        
        Args:
            transaction_id: Original transaction ID
            amount: Refund amount
            
        Returns:
            Tuple of (success, refund_id_or_error)
        """
        self._refund_count += 1
        
        # Mock implementation
        refund_id = f"REF-{transaction_id[:8]}-{self._refund_count:04d}"
        
        # Simulate API call
        print(f"[RefundAPI] Initiating refund: {refund_id} for ${amount:.2f}")
        
        return (True, refund_id)
    
    def check_refund_status(self, refund_id: str) -> RefundStatus:
        """Check status of a refund."""
        # Mock: always return approved for demo
        return RefundStatus.APPROVED


class NotificationService:
    """
    Interface for notification delivery (mock implementation).
    
    Supports email, SMS, and push notifications.
    """
    
    def __init__(self):
        """Initialize notification service."""
        self._sent_count = 0
    
    def send_email(
        self, 
        to: str, 
        subject: str, 
        body: str
    ) -> bool:
        """Send email notification."""
        self._sent_count += 1
        print(f"[Email] To: {to} | Subject: {subject}")
        return True
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS notification."""
        self._sent_count += 1
        print(f"[SMS] To: {phone_number} | Message: {message[:50]}...")
        return True
    
    def send_push_notification(
        self, 
        user_id: str, 
        message: str
    ) -> bool:
        """Send push notification."""
        self._sent_count += 1
        print(f"[Push] To User: {user_id} | Message: {message[:50]}...")
        return True


class DecisionRouter:
    """
    Routes decisions based on trust scores and executes appropriate actions.
    
    Routes:
    - Score > 0.9: Auto-refund via RefundAPI
    - Score < 0.5: Fraud alert to support agent
    - 0.5 <= Score <= 0.9: Manual review queue
    """
    
    def __init__(
        self,
        refund_api: Optional[RefundAPI] = None,
        notification_service: Optional[NotificationService] = None
    ):
        """
        Initialize decision router with external services.
        
        Args:
            refund_api: Refund API client
            notification_service: Notification service client
        """
        self._refund_api = refund_api or RefundAPI()
        self._notification_service = notification_service or NotificationService()
        self._routing_log: List[Dict] = []
    
    def route_decision(
        self, 
        dispute_id: str,
        trust_result: TrustScoreResult,
        user_email: Optional[str] = None,
        order_amount: float = 0.0
    ) -> Dict:
        """
        Route the decision based on trust score result.
        
        Args:
            dispute_id: Unique dispute identifier
            trust_result: Result from TrustScoreCalculator
            user_email: User's email for notifications
            order_amount: Order amount for refund processing
            
        Returns:
            Routing result dictionary
        """
        decision = trust_result.decision
        
        result = {
            "dispute_id": dispute_id,
            "decision": decision.value,
            "trust_score": trust_result.trust_score,
            "timestamp": datetime.now().isoformat(),
            "action_taken": None
        }
        
        if decision == DecisionType.AUTO_REFUND:
            success = self.process_auto_refund(dispute_id, order_amount, user_email)
            result["action_taken"] = "auto_refund_processed" if success else "refund_failed"
            
        elif decision == DecisionType.FRAUD_ALERT:
            alert = self.create_fraud_alert(dispute_id, trust_result)
            result["action_taken"] = "fraud_alert_created"
            result["alert_id"] = alert.alert_id
            
        else:  # MANUAL_REVIEW
            self.request_manual_review(dispute_id, trust_result)
            result["action_taken"] = "queued_for_manual_review"
        
        # Log the routing
        self._routing_log.append(result)
        
        return result
    
    def process_auto_refund(
        self, 
        dispute_id: str, 
        amount: float,
        user_email: Optional[str] = None
    ) -> bool:
        """
        Process automatic refund for high trust score disputes.
        
        Args:
            dispute_id: Dispute identifier
            amount: Refund amount
            user_email: Email for notification
            
        Returns:
            True if refund was successful
        """
        print(f"\n[AutoRefund] Processing refund for dispute: {dispute_id}")
        
        # Initiate refund
        success, refund_id = self._refund_api.initiate_refund(dispute_id, amount)
        
        if success and user_email:
            # Send notification
            self._notification_service.send_email(
                to=user_email,
                subject="Your Refund Has Been Approved!",
                body=f"Great news! Your refund request (ID: {refund_id}) "
                     f"for ${amount:.2f} has been approved and processed."
            )
        
        return success
    
    def create_fraud_alert(
        self, 
        dispute_id: str,
        trust_result: TrustScoreResult
    ) -> FraudAlert:
        """
        Create a fraud alert for support agent review.
        
        Args:
            dispute_id: Dispute identifier
            trust_result: Trust score calculation result
            
        Returns:
            Created FraudAlert object
        """
        print(f"\n[FraudAlert] Creating alert for dispute: {dispute_id}")
        
        # Determine priority based on score
        if trust_result.trust_score < 0.2:
            priority = "high"
        elif trust_result.trust_score < 0.35:
            priority = "medium"
        else:
            priority = "low"
        
        alert = FraudAlert(
            alert_id=f"ALERT-{dispute_id[:8]}-{datetime.now().strftime('%H%M%S')}",
            dispute_id=dispute_id,
            trust_score=trust_result.trust_score,
            flags=self._generate_flags(trust_result),
            priority=priority,
            created_at=datetime.now(),
            evidence_summary=trust_result.component_scores
        )
        
        # Notify duty agent (mock)
        self._notification_service.send_push_notification(
            user_id="duty_agent",
            message=f"[{priority.upper()}] New fraud alert: {alert.alert_id}"
        )
        
        return alert
    
    def request_manual_review(
        self, 
        dispute_id: str,
        trust_result: TrustScoreResult
    ) -> None:
        """
        Queue dispute for manual review by support agent.
        
        Args:
            dispute_id: Dispute identifier
            trust_result: Trust score calculation result
        """
        print(f"\n[ManualReview] Queuing dispute: {dispute_id} (score: {trust_result.trust_score:.2f})")
        
        # In production, this would add to a work queue
        # For demo, just log the request
        self._notification_service.send_push_notification(
            user_id="review_queue",
            message=f"New review request: {dispute_id} (confidence: {trust_result.confidence_level})"
        )
    
    def _generate_flags(self, trust_result: TrustScoreResult) -> List[str]:
        """Generate flags based on component scores."""
        flags = []
        scores = trust_result.component_scores
        
        if scores.get("metadata", 1) < 0.3:
            flags.append("SUSPICIOUS_METADATA")
        if scores.get("ela", 1) < 0.4:
            flags.append("IMAGE_MANIPULATION_DETECTED")
        if scores.get("ai", 1) < 0.5:
            flags.append("SEMANTIC_INCONSISTENCY")
        
        return flags


# Example usage and demonstration
if __name__ == "__main__":
    print("=" * 60)
    print("VeriSupport Trust Score Calculator - Demo")
    print("=" * 60)
    
    # Initialize calculator with default weights
    calculator = TrustScoreCalculator()
    router = DecisionRouter()
    
    print(f"\n[OK] TrustScoreCalculator initialized")
    print(f"    Weights: meta={calculator.weights.metadata_weight}, "
          f"ela={calculator.weights.ela_weight}, "
          f"ai={calculator.weights.ai_weight}")
    print(f"    Auto-refund threshold: {calculator.auto_refund_threshold}")
    print(f"    Fraud alert threshold: {calculator.fraud_alert_threshold}")
    
    # Test scenarios
    print("\n" + "-" * 60)
    print("Test Scenarios:")
    print("-" * 60)
    
    scenarios = [
        ("Authentic Image", 1.0, 0.95, 0.92),  # All high scores
        ("Manipulated Image", 0.0, 0.3, 0.4),  # Low scores = fraud
        ("Borderline Case", 0.5, 0.7, 0.6),     # Medium scores = manual review
    ]
    
    for name, s_meta, s_ela, s_ai in scenarios:
        result = calculator.calculate_trust_score(s_meta, s_ela, s_ai)
        
        print(f"\n[Scenario: {name}]")
        print(f"    Inputs: meta={s_meta}, ela={s_ela}, ai={s_ai}")
        print(f"    Trust Score: {result.trust_score:.3f}")
        print(f"    Decision: {result.decision.value}")
        print(f"    Confidence: {result.confidence_level}")
        
        # Route the decision
        dispute_id = f"DISP-{name.replace(' ', '-').upper()}"
        route_result = router.route_decision(
            dispute_id=dispute_id,
            trust_result=result,
            user_email="customer@example.com",
            order_amount=49.99
        )
        print(f"    Action: {route_result['action_taken']}")
    
    print("\n" + "=" * 60)
    print("Module loaded successfully!")
    print("=" * 60)
