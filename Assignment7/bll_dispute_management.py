"""
Business Logic Layer - Dispute Management Module
Handles all business rules and logic related to dispute processing.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 3"))
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 5"))

try:
    from forensic_analysis_service import ForensicAnalysisService
    from decision_engine_service import DecisionEngineService
except ImportError:
    print("Warning: Could not import service modules")


class DisputeManagementBLL:
    """
    Business Logic Layer for Dispute Management
    
    Responsibilities:
    - Validate dispute submissions
    - Orchestrate forensic analysis and decision making
    - Apply business rules for dispute processing
    - Transform data between layers
    """
    
    def __init__(self):
        """Initialize BLL with required services"""
        try:
            self.forensic_service = ForensicAnalysisService()
            self.decision_service = DecisionEngineService()
        except:
            self.forensic_service = None
            self.decision_service = None
        
        # Business rules configuration
        self.min_order_amount = 10.0
        self.max_order_amount = 10000.0
        self.max_description_length = 500
        self.allowed_image_formats = ['jpg', 'jpeg', 'png']
        self.max_image_size = 10 * 1024 * 1024  # 10MB
    
    def validate_dispute_submission(self, dispute_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate dispute submission data
        
        Business Rules:
        - Order ID must be provided and valid format
        - Amount must be between min and max limits
        - Description must not exceed max length
        - Image must be provided and valid format
        
        Args:
            dispute_data: Dictionary containing dispute information
            
        Returns:
            Dictionary with validation result and errors if any
        """
        errors = []
        
        # Validate Order ID
        order_id = dispute_data.get('order_id', '').strip()
        if not order_id:
            errors.append("Order ID is required")
        elif len(order_id) < 3:
            errors.append("Order ID must be at least 3 characters")
        
        # Validate Amount
        try:
            amount = float(dispute_data.get('amount', 0))
            if amount < self.min_order_amount:
                errors.append(f"Order amount must be at least ${self.min_order_amount}")
            elif amount > self.max_order_amount:
                errors.append(f"Order amount cannot exceed ${self.max_order_amount}")
        except (ValueError, TypeError):
            errors.append("Invalid amount format")
        
        # Validate Description
        description = dispute_data.get('description', '').strip()
        if not description:
            errors.append("Description is required")
        elif len(description) > self.max_description_length:
            errors.append(f"Description cannot exceed {self.max_description_length} characters")
        
        # Validate Image
        image_data = dispute_data.get('image_data')
        if not image_data:
            errors.append("Evidence image is required")
        elif len(image_data) > self.max_image_size:
            errors.append(f"Image size cannot exceed {self.max_image_size / (1024*1024)}MB")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def process_dispute(self, dispute_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a dispute submission through the complete workflow
        
        Business Logic Flow:
        1. Validate input data
        2. Generate dispute ID
        3. Perform forensic analysis
        4. Calculate trust score and decision
        5. Apply business rules for final decision
        6. Transform data for presentation layer
        
        Args:
            dispute_data: Dictionary containing dispute information
            
        Returns:
            Processed dispute result with decision
        """
        # Step 1: Validate
        validation = self.validate_dispute_submission(dispute_data)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        # Step 2: Generate Dispute ID
        dispute_id = self._generate_dispute_id()
        
        # Step 3: Forensic Analysis
        try:
            forensic_result = self.forensic_service.analyze(
                dispute_data['image_data'],
                dispute_id
            )
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Forensic analysis failed: {str(e)}"]
            }
        
        # Step 4: Decision Calculation
        try:
            decision_result = self.decision_service.process_scores(
                metadata_score=forensic_result['metadata_score'],
                ela_score=forensic_result['ela_score'],
                ai_score=forensic_result.get('ai_score', 0.75),
                order_amount=float(dispute_data['amount']),
                dispute_id=dispute_id
            )
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Decision calculation failed: {str(e)}"]
            }
        
        # Step 5: Apply Business Rules
        final_decision = self._apply_business_rules(
            decision_result,
            dispute_data,
            forensic_result
        )
        
        # Step 6: Transform for Presentation Layer
        return self._transform_for_presentation(
            dispute_id,
            dispute_data,
            forensic_result,
            final_decision
        )
    
    def _generate_dispute_id(self) -> str:
        """Generate unique dispute ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"DISP-{timestamp}"
    
    def _apply_business_rules(
        self,
        decision_result: Dict[str, Any],
        dispute_data: Dict[str, Any],
        forensic_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply additional business rules to the decision
        
        Business Rules:
        - High-value orders (>$500) require manual review even with high trust
        - Multiple fraud flags trigger automatic rejection
        - Low metadata score (<0.3) triggers fraud alert regardless of other scores
        """
        trust_score = decision_result.get('trust_score', 0)
        decision = decision_result.get('decision', 'manual_review')
        amount = float(dispute_data.get('amount', 0))
        
        # Rule 1: High-value orders
        if amount > 500 and decision == 'auto_refund':
            decision = 'manual_review'
            decision_result['reason'] = 'High-value order requires manual verification'
        
        # Rule 2: Multiple fraud flags
        fraud_flags = forensic_result.get('flags', [])
        if len(fraud_flags) >= 3:
            decision = 'fraud_alert'
            decision_result['reason'] = 'Multiple fraud indicators detected'
        
        # Rule 3: Low metadata score
        if forensic_result.get('metadata_score', 1.0) < 0.3:
            decision = 'fraud_alert'
            decision_result['reason'] = 'Image metadata indicates manipulation'
        
        decision_result['decision'] = decision
        return decision_result
    
    def _transform_for_presentation(
        self,
        dispute_id: str,
        dispute_data: Dict[str, Any],
        forensic_result: Dict[str, Any],
        decision_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform data from service layer to presentation layer format
        
        Converts technical data into user-friendly format
        """
        trust_score = float(decision_result.get('trust_score', 0))
        decision = decision_result.get('decision', 'manual_review')
        
        # Map decision to user-friendly status
        status_map = {
            'auto_refund': 'Approved',
            'manual_review': 'Under Review',
            'fraud_alert': 'Rejected'
        }
        
        # Map decision to confidence level
        confidence_map = {
            'auto_refund': 'High',
            'manual_review': 'Medium',
            'fraud_alert': 'Low'
        }
        
        # Generate user-friendly recommendations
        recommendations = self._generate_recommendations(decision, trust_score)
        
        return {
            'success': True,
            'dispute_id': dispute_id,
            'status': status_map.get(decision, 'Unknown'),
            'trust_score': round(trust_score * 100, 2),
            'confidence': confidence_map.get(decision, 'Medium'),
            'decision': decision,
            'forensic_analysis': {
                'metadata_score': round(forensic_result.get('metadata_score', 0) * 100, 2),
                'ela_score': round(forensic_result.get('ela_score', 0) * 100, 2),
                'ai_score': round(forensic_result.get('ai_score', 0.75) * 100, 2),
                'risk_level': forensic_result.get('risk_level', 'unknown'),
                'flags': forensic_result.get('flags', [])
            },
            'decision_details': {
                'formula': decision_result.get('formula', ''),
                'action': decision_result.get('action', ''),
                'reason': decision_result.get('reason', '')
            },
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, decision: str, trust_score: float) -> List[str]:
        """Generate user-friendly recommendations based on decision"""
        if decision == 'auto_refund':
            return [
                "Your refund has been automatically approved",
                "Funds will be credited within 3-5 business days",
                "You will receive a confirmation email shortly"
            ]
        elif decision == 'fraud_alert':
            return [
                "This dispute requires additional verification",
                "Please provide additional evidence if available",
                "A support agent will contact you within 24 hours"
            ]
        else:
            return [
                "Your dispute is under review",
                "Expected review time: 24-48 hours",
                "You will be notified of the decision via email"
            ]
    
    def get_dispute_status(self, dispute_id: str) -> Dict[str, Any]:
        """
        Get current status of a dispute
        
        Args:
            dispute_id: Unique dispute identifier
            
        Returns:
            Current dispute status and details
        """
        # In a real system, this would query a database
        # For now, return a mock response
        return {
            'dispute_id': dispute_id,
            'status': 'Under Review',
            'last_updated': datetime.now().isoformat()
        }
    
    def list_disputes(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List disputes with optional filters
        
        Args:
            user_id: Filter by user ID
            status: Filter by status
            limit: Maximum number of results
            
        Returns:
            List of disputes
        """
        # In a real system, this would query a database
        # For now, return mock data
        return [
            {
                'dispute_id': f'DISP-{i:04d}',
                'order_id': f'ORD-{i:04d}',
                'status': 'Approved' if i % 3 == 0 else 'Under Review' if i % 3 == 1 else 'Rejected',
                'trust_score': 50 + (i % 5) * 10,
                'amount': 25.00 + i * 5,
                'timestamp': datetime.now().isoformat()
            }
            for i in range(1, min(limit + 1, 11))
        ]


if __name__ == "__main__":
    # Test the BLL
    print("Testing Dispute Management BLL")
    print("-" * 50)
    
    bll = DisputeManagementBLL()
    
    # Test validation
    test_data = {
        'order_id': 'ORD-12345',
        'amount': 45.99,
        'description': 'Food was cold and had hair in it',
        'restaurant': 'Test Restaurant',
        'image_data': b'fake_image_data'
    }
    
    validation = bll.validate_dispute_submission(test_data)
    print(f"Validation Result: {validation}")
    
    print("\nDispute Management BLL test complete")
