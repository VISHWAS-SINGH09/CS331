"""
Business Logic Layer - Decision Engine Module
Handles business rules and logic for refund decision making.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 3"))
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 5"))

try:
    from trust_score_calculator import TrustScoreCalculator
    from decision_engine_service import DecisionEngineService
except ImportError:
    print("Warning: Could not import decision modules")


class DecisionEngineBLL:
    """
    Business Logic Layer for Decision Engine
    
    Responsibilities:
    - Apply business rules for refund decisions
    - Calculate trust scores with business context
    - Handle special cases and exceptions
    - Transform decisions for presentation
    """
    
    def __init__(self):
        """Initialize BLL with decision services"""
        try:
            self.trust_calculator = TrustScoreCalculator()
            self.decision_service = DecisionEngineService()
        except:
            self.trust_calculator = None
            self.decision_service = None
        
        # Business rules configuration
        self.auto_refund_threshold = 0.90  # 90% trust score
        self.fraud_alert_threshold = 0.50  # Below 50% is fraud alert
        self.high_value_threshold = 500.0  # Orders above this need review
        self.max_auto_refund_amount = 1000.0  # Max amount for auto-refund
    
    def calculate_decision(
        self,
        metadata_score: float,
        ela_score: float,
        ai_score: float,
        order_amount: float,
        user_history: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate refund decision with business logic
        
        Business Logic Flow:
        1. Validate input scores
        2. Calculate base trust score
        3. Apply user history adjustments
        4. Apply business rules
        5. Determine final decision
        6. Transform for presentation
        
        Args:
            metadata_score: EXIF metadata score (0-1)
            ela_score: Error Level Analysis score (0-1)
            ai_score: AI analysis score (0-1)
            order_amount: Order amount in dollars
            user_history: Optional user history data
            
        Returns:
            Decision result with business context
        """
        # Step 1: Validate
        validation = self._validate_scores(metadata_score, ela_score, ai_score, order_amount)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        # Step 2: Calculate base trust score
        trust_score = self._calculate_trust_score(metadata_score, ela_score, ai_score)
        
        # Step 3: Apply user history adjustments
        if user_history:
            trust_score = self._apply_user_history_adjustment(trust_score, user_history)
        
        # Step 4: Apply business rules
        decision_data = self._apply_decision_rules(trust_score, order_amount)
        
        # Step 5: Transform for presentation
        return self._transform_decision_result(
            trust_score,
            decision_data,
            metadata_score,
            ela_score,
            ai_score,
            order_amount
        )
    
    def _validate_scores(
        self,
        metadata_score: float,
        ela_score: float,
        ai_score: float,
        order_amount: float
    ) -> Dict[str, Any]:
        """
        Validate input scores
        
        Business Rules:
        - All scores must be between 0 and 1
        - Order amount must be positive
        """
        errors = []
        
        if not (0 <= metadata_score <= 1):
            errors.append("Metadata score must be between 0 and 1")
        
        if not (0 <= ela_score <= 1):
            errors.append("ELA score must be between 0 and 1")
        
        if not (0 <= ai_score <= 1):
            errors.append("AI score must be between 0 and 1")
        
        if order_amount <= 0:
            errors.append("Order amount must be positive")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _calculate_trust_score(
        self,
        metadata_score: float,
        ela_score: float,
        ai_score: float
    ) -> float:
        """
        Calculate trust score using weighted formula
        
        Formula: T = 0.20(M) + 0.35(E) + 0.45(A)
        Where:
        - M = Metadata score
        - E = ELA score
        - A = AI score
        """
        trust_score = (
            0.20 * metadata_score +
            0.35 * ela_score +
            0.45 * ai_score
        )
        return trust_score
    
    def _apply_user_history_adjustment(
        self,
        trust_score: float,
        user_history: Dict[str, Any]
    ) -> float:
        """
        Adjust trust score based on user history
        
        Business Rules:
        - Users with good history get +5% boost
        - Users with fraud history get -10% penalty
        - New users get no adjustment
        """
        history_type = user_history.get('type', 'new')
        
        if history_type == 'good':
            # Boost for good users, but cap at 1.0
            trust_score = min(1.0, trust_score + 0.05)
        elif history_type == 'fraud':
            # Penalty for users with fraud history
            trust_score = max(0.0, trust_score - 0.10)
        
        return trust_score
    
    def _apply_decision_rules(
        self,
        trust_score: float,
        order_amount: float
    ) -> Dict[str, Any]:
        """
        Apply business rules to determine final decision
        
        Business Rules:
        1. Trust >= 90% AND amount <= $1000 -> Auto-refund
        2. Trust >= 90% AND amount > $1000 -> Manual review (high value)
        3. Trust >= 50% AND < 90% -> Manual review
        4. Trust < 50% -> Fraud alert
        5. Amount > $500 always requires review regardless of trust
        """
        decision = 'manual_review'
        reason = ''
        action = ''
        confidence = 'medium'
        
        # Rule 5: High-value orders (overrides other rules)
        if order_amount > self.high_value_threshold:
            decision = 'manual_review'
            reason = 'High-value order requires manual verification'
            action = 'queued_for_review'
            confidence = 'medium'
        
        # Rule 1: Auto-refund
        elif trust_score >= self.auto_refund_threshold and order_amount <= self.max_auto_refund_amount:
            decision = 'auto_refund'
            reason = 'High trust score indicates authentic claim'
            action = 'refund_approved'
            confidence = 'high'
        
        # Rule 2: High trust but high value
        elif trust_score >= self.auto_refund_threshold:
            decision = 'manual_review'
            reason = 'High trust but amount exceeds auto-refund limit'
            action = 'queued_for_review'
            confidence = 'high'
        
        # Rule 3: Medium trust
        elif trust_score >= self.fraud_alert_threshold:
            decision = 'manual_review'
            reason = 'Moderate trust score requires human verification'
            action = 'queued_for_review'
            confidence = 'medium'
        
        # Rule 4: Low trust
        else:
            decision = 'fraud_alert'
            reason = 'Low trust score indicates possible fraud'
            action = 'flagged_for_investigation'
            confidence = 'low'
        
        return {
            'decision': decision,
            'reason': reason,
            'action': action,
            'confidence': confidence
        }
    
    def _transform_decision_result(
        self,
        trust_score: float,
        decision_data: Dict[str, Any],
        metadata_score: float,
        ela_score: float,
        ai_score: float,
        order_amount: float
    ) -> Dict[str, Any]:
        """
        Transform decision result for presentation layer
        
        Converts technical decision into user-friendly format
        """
        decision = decision_data['decision']
        
        # Map decision to user-friendly message
        message_map = {
            'auto_refund': 'Refund Approved - Your claim has been verified as authentic',
            'manual_review': 'Under Review - A support agent will review your claim within 24-48 hours',
            'fraud_alert': 'Additional Verification Required - Please contact support for assistance'
        }
        
        # Generate next steps
        next_steps = self._generate_next_steps(decision, trust_score)
        
        # Calculate estimated processing time
        processing_time = self._estimate_processing_time(decision)
        
        return {
            'success': True,
            'trust_score': round(trust_score * 100, 2),
            'decision': decision,
            'confidence': decision_data['confidence'],
            'message': message_map.get(decision, 'Processing'),
            'reason': decision_data['reason'],
            'action': decision_data['action'],
            'score_breakdown': {
                'metadata': {
                    'score': round(metadata_score * 100, 2),
                    'weight': '20%',
                    'contribution': round(metadata_score * 20, 2)
                },
                'ela': {
                    'score': round(ela_score * 100, 2),
                    'weight': '35%',
                    'contribution': round(ela_score * 35, 2)
                },
                'ai': {
                    'score': round(ai_score * 100, 2),
                    'weight': '45%',
                    'contribution': round(ai_score * 45, 2)
                }
            },
            'formula': f"Trust Score = (0.20 × {metadata_score:.2f}) + (0.35 × {ela_score:.2f}) + (0.45 × {ai_score:.2f}) = {trust_score:.2f}",
            'next_steps': next_steps,
            'estimated_processing_time': processing_time,
            'order_amount': order_amount,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_next_steps(self, decision: str, trust_score: float) -> list:
        """Generate next steps based on decision"""
        if decision == 'auto_refund':
            return [
                "Your refund will be processed automatically",
                "Funds will be credited to your original payment method",
                "You will receive a confirmation email",
                "Estimated time: 3-5 business days"
            ]
        elif decision == 'fraud_alert':
            return [
                "A support agent will contact you within 24 hours",
                "Please prepare additional evidence if available",
                "Check your email for updates",
                "You may be asked to provide more information"
            ]
        else:
            return [
                "Your claim is in the review queue",
                "A support agent will review within 24-48 hours",
                "You will receive an email notification",
                "No action required from your side"
            ]
    
    def _estimate_processing_time(self, decision: str) -> str:
        """Estimate processing time based on decision"""
        time_map = {
            'auto_refund': 'Immediate (3-5 business days for funds)',
            'manual_review': '24-48 hours',
            'fraud_alert': '24-72 hours'
        }
        return time_map.get(decision, 'Unknown')
    
    def recalculate_with_override(
        self,
        original_decision: Dict[str, Any],
        override_reason: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Allow manual override of automated decision
        
        Business Use Case:
        - Support agents can override automated decisions
        - Requires reason and agent ID for audit trail
        
        Args:
            original_decision: Original automated decision
            override_reason: Reason for override
            agent_id: ID of agent making override
            
        Returns:
            Updated decision with override information
        """
        return {
            'success': True,
            'original_decision': original_decision.get('decision'),
            'overridden': True,
            'override_reason': override_reason,
            'agent_id': agent_id,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about decisions made
        
        Business Use Case:
        - Monitor fraud detection effectiveness
        - Track auto-refund vs manual review rates
        - Identify trends
        
        Returns:
            Decision statistics
        """
        # In real system, would query database
        return {
            'total_decisions': 1000,
            'auto_refunds': 450,
            'manual_reviews': 400,
            'fraud_alerts': 150,
            'average_trust_score': 0.72,
            'auto_refund_rate': 0.45,
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the BLL
    print("Testing Decision Engine BLL")
    print("-" * 50)
    
    bll = DecisionEngineBLL()
    
    # Test decision calculation
    result = bll.calculate_decision(
        metadata_score=0.85,
        ela_score=0.78,
        ai_score=0.92,
        order_amount=45.99
    )
    
    print(f"Decision Result: {result.get('decision')}")
    print(f"Trust Score: {result.get('trust_score')}%")
    print(f"Confidence: {result.get('confidence')}")
    
    print("\nDecision Engine BLL test complete")
