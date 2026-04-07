"""
Business Logic Layer - Forensic Analysis Module
Handles business rules and logic for image forensic analysis.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 3"))
sys.path.insert(0, str(Path(__file__).parent.parent / "Assignment 5"))

try:
    from forensic_engine import ForensicEngine
    from forensic_analysis_service import ForensicAnalysisService
except ImportError:
    print("Warning: Could not import forensic modules")


class ForensicAnalysisBLL:
    """
    Business Logic Layer for Forensic Analysis
    
    Responsibilities:
    - Validate image data before analysis
    - Apply business rules for forensic analysis
    - Transform forensic results for business use
    - Handle edge cases and error scenarios
    """
    
    def __init__(self):
        """Initialize BLL with forensic services"""
        try:
            self.forensic_engine = ForensicEngine()
            self.forensic_service = ForensicAnalysisService()
        except:
            self.forensic_engine = None
            self.forensic_service = None
        
        # Business rules configuration
        self.min_image_size = 1024  # 1KB
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.supported_formats = ['JPEG', 'PNG', 'JPG']
        self.min_acceptable_metadata_score = 0.3
        self.min_acceptable_ela_score = 0.4
    
    def validate_image_data(self, image_data: bytes) -> Dict[str, Any]:
        """
        Validate image data before forensic analysis
        
        Business Rules:
        - Image size must be within acceptable range
        - Image must be in supported format
        - Image must be readable
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Validation result with errors if any
        """
        errors = []
        
        # Check image size
        if len(image_data) < self.min_image_size:
            errors.append(f"Image too small (minimum {self.min_image_size} bytes)")
        elif len(image_data) > self.max_image_size:
            errors.append(f"Image too large (maximum {self.max_image_size / (1024*1024)}MB)")
        
        # Try to validate image format
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_data))
            if img.format not in self.supported_formats:
                errors.append(f"Unsupported format: {img.format}. Supported: {', '.join(self.supported_formats)}")
        except Exception as e:
            errors.append(f"Invalid image data: {str(e)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def analyze_image(
        self,
        image_data: bytes,
        reference_id: str,
        include_detailed_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Perform forensic analysis on image with business logic
        
        Business Logic Flow:
        1. Validate image data
        2. Perform forensic analysis
        3. Apply business rules to results
        4. Transform results for business use
        
        Args:
            image_data: Raw image bytes
            reference_id: Unique identifier for this analysis
            include_detailed_analysis: Whether to include detailed breakdown
            
        Returns:
            Forensic analysis results with business context
        """
        # Step 1: Validate
        validation = self.validate_image_data(image_data)
        if not validation['valid']:
            return {
                'success': False,
                'errors': validation['errors']
            }
        
        # Step 2: Perform Analysis
        try:
            forensic_result = self.forensic_service.analyze(image_data, reference_id)
        except Exception as e:
            return {
                'success': False,
                'errors': [f"Analysis failed: {str(e)}"]
            }
        
        # Step 3: Apply Business Rules
        enhanced_result = self._apply_forensic_business_rules(forensic_result)
        
        # Step 4: Transform for Business Use
        return self._transform_forensic_results(
            enhanced_result,
            reference_id,
            include_detailed_analysis
        )
    
    def _apply_forensic_business_rules(self, forensic_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply business rules to forensic analysis results
        
        Business Rules:
        - Metadata score below threshold triggers warning
        - ELA score below threshold indicates manipulation
        - Combination of low scores escalates risk level
        - Missing EXIF data is suspicious for recent photos
        """
        metadata_score = forensic_result.get('metadata_score', 0)
        ela_score = forensic_result.get('ela_score', 0)
        flags = forensic_result.get('flags', [])
        
        # Rule 1: Low metadata score
        if metadata_score < self.min_acceptable_metadata_score:
            if 'Low metadata score - possible manipulation' not in flags:
                flags.append('Low metadata score - possible manipulation')
        
        # Rule 2: Low ELA score
        if ela_score < self.min_acceptable_ela_score:
            if 'Low ELA score - editing detected' not in flags:
                flags.append('Low ELA score - editing detected')
        
        # Rule 3: Combined low scores
        if metadata_score < 0.4 and ela_score < 0.5:
            forensic_result['risk_level'] = 'high'
            if 'Multiple indicators of manipulation' not in flags:
                flags.append('Multiple indicators of manipulation')
        
        # Rule 4: Missing critical EXIF data
        if metadata_score < 0.2:
            if 'Critical EXIF data missing' not in flags:
                flags.append('Critical EXIF data missing')
        
        forensic_result['flags'] = flags
        return forensic_result
    
    def _transform_forensic_results(
        self,
        forensic_result: Dict[str, Any],
        reference_id: str,
        include_detailed: bool
    ) -> Dict[str, Any]:
        """
        Transform forensic results into business-friendly format
        
        Converts technical scores into actionable business information
        """
        metadata_score = forensic_result.get('metadata_score', 0)
        ela_score = forensic_result.get('ela_score', 0)
        ai_score = forensic_result.get('ai_score', 0.75)
        
        # Calculate overall authenticity score
        overall_score = (0.20 * metadata_score + 0.35 * ela_score + 0.45 * ai_score)
        
        # Determine authenticity level
        if overall_score >= 0.8:
            authenticity = 'High - Likely authentic'
        elif overall_score >= 0.5:
            authenticity = 'Medium - Requires review'
        else:
            authenticity = 'Low - Likely manipulated'
        
        result = {
            'success': True,
            'reference_id': reference_id,
            'overall_authenticity_score': round(overall_score * 100, 2),
            'authenticity_level': authenticity,
            'component_scores': {
                'metadata': {
                    'score': round(metadata_score * 100, 2),
                    'weight': '20%',
                    'interpretation': self._interpret_metadata_score(metadata_score)
                },
                'ela': {
                    'score': round(ela_score * 100, 2),
                    'weight': '35%',
                    'interpretation': self._interpret_ela_score(ela_score)
                },
                'ai_analysis': {
                    'score': round(ai_score * 100, 2),
                    'weight': '45%',
                    'interpretation': self._interpret_ai_score(ai_score)
                }
            },
            'risk_level': forensic_result.get('risk_level', 'unknown'),
            'flags': forensic_result.get('flags', []),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add detailed analysis if requested
        if include_detailed:
            result['detailed_analysis'] = self._generate_detailed_analysis(forensic_result)
        
        return result
    
    def _interpret_metadata_score(self, score: float) -> str:
        """Interpret metadata score for business users"""
        if score >= 0.8:
            return "Excellent - Complete camera metadata present"
        elif score >= 0.5:
            return "Good - Most metadata intact"
        elif score >= 0.3:
            return "Fair - Some metadata missing"
        else:
            return "Poor - Critical metadata missing or altered"
    
    def _interpret_ela_score(self, score: float) -> str:
        """Interpret ELA score for business users"""
        if score >= 0.8:
            return "Excellent - No editing detected"
        elif score >= 0.5:
            return "Good - Minimal compression artifacts"
        elif score >= 0.3:
            return "Fair - Some inconsistencies detected"
        else:
            return "Poor - Significant editing detected"
    
    def _interpret_ai_score(self, score: float) -> str:
        """Interpret AI score for business users"""
        if score >= 0.8:
            return "Excellent - Highly likely authentic"
        elif score >= 0.5:
            return "Good - Appears authentic"
        elif score >= 0.3:
            return "Fair - Some concerns"
        else:
            return "Poor - Likely AI-generated or heavily edited"
    
    def _generate_detailed_analysis(self, forensic_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed technical analysis for advanced users"""
        return {
            'exif_data_present': forensic_result.get('metadata_score', 0) > 0.5,
            'compression_analysis': {
                'uniform': forensic_result.get('ela_score', 0) > 0.7,
                'artifacts_detected': forensic_result.get('ela_score', 0) < 0.5
            },
            'manipulation_indicators': forensic_result.get('flags', []),
            'confidence_level': 'high' if forensic_result.get('metadata_score', 0) > 0.7 else 'medium'
        }
    
    def compare_images(
        self,
        image1_data: bytes,
        image2_data: bytes,
        reference_id: str
    ) -> Dict[str, Any]:
        """
        Compare two images for similarity (useful for detecting reused fraud images)
        
        Business Use Case:
        - Detect if same image is being used for multiple fraud claims
        - Identify patterns in fraudulent submissions
        
        Args:
            image1_data: First image bytes
            image2_data: Second image bytes
            reference_id: Unique identifier for comparison
            
        Returns:
            Comparison results
        """
        # Validate both images
        val1 = self.validate_image_data(image1_data)
        val2 = self.validate_image_data(image2_data)
        
        if not val1['valid'] or not val2['valid']:
            return {
                'success': False,
                'errors': val1['errors'] + val2['errors']
            }
        
        # Perform comparison (simplified for now)
        # In real system, would use perceptual hashing or similar
        similarity_score = 0.0  # Placeholder
        
        return {
            'success': True,
            'reference_id': reference_id,
            'similarity_score': similarity_score,
            'likely_duplicate': similarity_score > 0.95,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_analysis_summary(self, reference_id: str) -> Dict[str, Any]:
        """
        Get summary of previous analysis
        
        Args:
            reference_id: Unique identifier for analysis
            
        Returns:
            Analysis summary
        """
        # In real system, would retrieve from database
        return {
            'reference_id': reference_id,
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the BLL
    print("Testing Forensic Analysis BLL")
    print("-" * 50)
    
    bll = ForensicAnalysisBLL()
    
    # Test validation
    test_data = b'fake_image_data_for_testing'
    validation = bll.validate_image_data(test_data)
    print(f"Validation Result: {validation}")
    
    print("\nForensic Analysis BLL test complete")
