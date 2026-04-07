"""
VeriSupport - Forensic Analysis Engine Module

This module implements the Forensic Analysis Engine for detecting manipulated images.
It includes:
- MetadataAnalyzer: Parses EXIF data and detects software signatures
- ELAProcessor: Performs Error Level Analysis for compression artifact detection
- ForensicEngine: Orchestrates both analyses

Author: VeriSupport Team
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum
import hashlib
import io

# Optional imports for image processing
try:
    from PIL import Image, ImageChops
    import numpy as np
    HAS_IMAGING = True
except ImportError:
    HAS_IMAGING = False
    print("Warning: PIL/numpy not available. Image processing features disabled.")


class AnalysisStatus(Enum):
    """Status of forensic analysis."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class ExifData:
    """Container for extracted EXIF metadata."""
    make: Optional[str] = None
    model: Optional[str] = None
    software: Optional[str] = None
    datetime_original: Optional[str] = None
    gps_info: Optional[Dict] = None
    has_thumbnail: bool = False
    raw_data: Optional[Dict] = None


@dataclass
class ELAResult:
    """Result of Error Level Analysis."""
    variance_score: float  # 0.0 - 1.0, lower is more authentic
    max_difference: float
    mean_difference: float
    suspicious_regions: List[Tuple[int, int, int, int]]  # (x, y, width, height)
    ela_image_data: Optional[bytes] = None


@dataclass
class ForensicResult:
    """Combined result of all forensic analyses."""
    metadata_score: float  # 0.0 or 1.0 (binary)
    ela_score: float  # 0.0 - 1.0, normalized
    image_hash: str
    status: AnalysisStatus
    flags: List[str]
    details: Dict


class MetadataAnalyzer:
    """
    Analyzes image metadata (EXIF) to detect potential manipulation.
    
    Checks for:
    - Software signatures (Adobe, GIMP, Stable Diffusion, etc.)
    - Missing or stripped metadata
    - Inconsistent timestamps
    """
    
    # Software signatures that indicate potential manipulation
    SUSPICIOUS_SOFTWARE: List[str] = [
        "adobe", "photoshop", "gimp", "canva", "pixlr",
        "stable diffusion", "midjourney", "dall-e", "dalle",
        "figma", "sketch", "affinity", "paint.net", "lightroom",
        "illustrator", "inpaint", "remove.bg", "photoroom"
    ]
    
    # Required fields for authentic camera photos
    CAMERA_FIELDS: List[str] = [
        "Make", "Model", "DateTime", "DateTimeOriginal"
    ]
    
    def __init__(self):
        """Initialize the metadata analyzer."""
        self._analysis_count = 0
    
    def extract_exif(self, image_data: bytes) -> ExifData:
        """
        Extract EXIF metadata from image bytes.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            ExifData object with extracted metadata
        """
        if not HAS_IMAGING:
            return ExifData(raw_data={"error": "Imaging library not available"})
        
        try:
            img = Image.open(io.BytesIO(image_data))
            exif_dict = {}
            
            # Try to get EXIF data
            if hasattr(img, '_getexif') and img._getexif():
                exif_dict = img._getexif()
            
            # Extract key fields
            return ExifData(
                make=exif_dict.get(271),  # EXIF tag for Make
                model=exif_dict.get(272),  # EXIF tag for Model
                software=exif_dict.get(305),  # EXIF tag for Software
                datetime_original=exif_dict.get(36867),  # DateTimeOriginal
                has_thumbnail='thumbnail' in str(img.info).lower(),
                raw_data=exif_dict if exif_dict else None
            )
        except Exception as e:
            return ExifData(raw_data={"error": str(e)})
    
    def detect_software_signatures(self, exif: ExifData) -> Tuple[bool, List[str]]:
        """
        Detect suspicious software signatures in metadata.
        
        Args:
            exif: Extracted EXIF data
            
        Returns:
            Tuple of (is_suspicious, list_of_detected_software)
        """
        detected = []
        
        # Check software field
        if exif.software:
            software_lower = exif.software.lower()
            for suspicious in self.SUSPICIOUS_SOFTWARE:
                if suspicious in software_lower:
                    detected.append(exif.software)
                    break
        
        # Check raw data for any suspicious strings
        if exif.raw_data:
            raw_str = str(exif.raw_data).lower()
            for suspicious in self.SUSPICIOUS_SOFTWARE:
                if suspicious in raw_str and suspicious not in [d.lower() for d in detected]:
                    detected.append(suspicious)
        
        return (len(detected) > 0, detected)
    
    def validate_source(self, exif: ExifData) -> float:
        """
        Validate if the image appears to be from an authentic source.
        
        Args:
            exif: Extracted EXIF data
            
        Returns:
            Score from 0.0 (invalid) to 1.0 (valid authentic source)
        """
        # Start with neutral score
        score = 0.5
        
        # Check for camera make/model (authentic indicator)
        if exif.make and exif.model:
            score += 0.3
        
        # Check for original datetime (authentic indicator)
        if exif.datetime_original:
            score += 0.2
        
        # Check for suspicious software (fraud indicator)
        is_suspicious, _ = self.detect_software_signatures(exif)
        if is_suspicious:
            score = 0.0  # Immediate fail
        
        # No metadata at all is suspicious
        if not exif.raw_data or exif.raw_data.get("error"):
            score = max(0.0, score - 0.3)
        
        return min(1.0, max(0.0, score))
    
    def analyze(self, image_data: bytes) -> Tuple[float, Dict]:
        """
        Perform complete metadata analysis.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Tuple of (metadata_score, analysis_details)
        """
        self._analysis_count += 1
        
        exif = self.extract_exif(image_data)
        is_suspicious, detected_software = self.detect_software_signatures(exif)
        source_score = self.validate_source(exif)
        
        # Binary score: 1.0 if valid, 0.0 if suspicious
        metadata_score = 0.0 if is_suspicious else (1.0 if source_score > 0.5 else 0.0)
        
        details = {
            "make": exif.make,
            "model": exif.model,
            "software": exif.software,
            "datetime_original": exif.datetime_original,
            "is_suspicious": is_suspicious,
            "detected_software": detected_software,
            "source_validation_score": source_score,
            "has_metadata": exif.raw_data is not None
        }
        
        return (metadata_score, details)


class ELAProcessor:
    """
    Performs Error Level Analysis (ELA) to detect image manipulation.
    
    ELA works by:
    1. Resaving the image at a known quality (90%)
    2. Calculating pixel differences between original and resaved
    3. Amplifying these differences (x50)
    4. Authentic images show uniform noise; manipulated regions glow
    """
    
    def __init__(
        self,
        resave_quality: int = 90,
        amplification_factor: int = 50,
        threshold_variance: float = 0.15
    ):
        """
        Initialize ELA processor.
        
        Args:
            resave_quality: JPEG quality for resaving (default 90)
            amplification_factor: Factor to multiply differences (default 50)
            threshold_variance: Variance threshold for suspicious regions (default 0.15)
        """
        self._resave_quality = resave_quality
        self._amplification_factor = amplification_factor
        self._threshold_variance = threshold_variance
        self._analysis_count = 0
    
    @property
    def resave_quality(self) -> int:
        return self._resave_quality
    
    @property
    def amplification_factor(self) -> int:
        return self._amplification_factor
    
    def perform_ela(self, image_data: bytes) -> ELAResult:
        """
        Perform Error Level Analysis on an image.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            ELAResult with analysis metrics
        """
        self._analysis_count += 1
        
        if not HAS_IMAGING:
            return ELAResult(
                variance_score=0.5,
                max_difference=0,
                mean_difference=0,
                suspicious_regions=[]
            )
        
        try:
            # Open original image
            original = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if original.mode != 'RGB':
                original = original.convert('RGB')
            
            # Resave at known quality
            buffer = io.BytesIO()
            original.save(buffer, format='JPEG', quality=self._resave_quality)
            buffer.seek(0)
            resaved = Image.open(buffer)
            
            # Calculate pixel differences
            diff_matrix = self.calculate_pixel_difference(original, resaved)
            
            # Amplify differences
            amplified = self.amplify_differences(diff_matrix)
            
            # Compute variance score
            variance_score = self.compute_variance_score(amplified)
            
            # Find suspicious regions
            suspicious_regions = self._find_suspicious_regions(amplified)
            
            # Calculate statistics
            max_diff = float(np.max(amplified)) if HAS_IMAGING else 0
            mean_diff = float(np.mean(amplified)) if HAS_IMAGING else 0
            
            # Create ELA visualization
            ela_image = self._create_ela_image(amplified)
            
            return ELAResult(
                variance_score=variance_score,
                max_difference=max_diff,
                mean_difference=mean_diff,
                suspicious_regions=suspicious_regions,
                ela_image_data=ela_image
            )
            
        except Exception as e:
            return ELAResult(
                variance_score=0.5,
                max_difference=0,
                mean_difference=0,
                suspicious_regions=[],
            )
    
    def calculate_pixel_difference(
        self, 
        original: 'Image.Image', 
        resaved: 'Image.Image'
    ) -> 'np.ndarray':
        """
        Calculate pixel-by-pixel difference between original and resaved.
        
        Args:
            original: Original PIL Image
            resaved: Resaved PIL Image
            
        Returns:
            Numpy array of differences
        """
        if not HAS_IMAGING:
            return None
        
        # Get difference image
        diff = ImageChops.difference(original, resaved)
        
        # Convert to numpy array
        diff_array = np.array(diff, dtype=np.float32)
        
        return diff_array
    
    def amplify_differences(self, diff_matrix: 'np.ndarray') -> 'np.ndarray':
        """
        Amplify the difference matrix by the amplification factor.
        
        Args:
            diff_matrix: Raw difference matrix
            
        Returns:
            Amplified difference matrix
        """
        if diff_matrix is None or not HAS_IMAGING:
            return None
        
        # Amplify and clip to valid range
        amplified = diff_matrix * self._amplification_factor
        amplified = np.clip(amplified, 0, 255)
        
        return amplified
    
    def compute_variance_score(self, amplified: 'np.ndarray') -> float:
        """
        Compute normalized variance score from amplified differences.
        
        Lower variance = more uniform = more likely authentic
        Higher variance = non-uniform = more likely manipulated
        
        Args:
            amplified: Amplified difference matrix
            
        Returns:
            Normalized variance score (0.0 - 1.0)
        """
        if amplified is None or not HAS_IMAGING:
            return 0.5
        
        # Calculate variance across all pixels
        variance = np.var(amplified)
        
        # Normalize to 0-1 range (empirically tuned)
        # Lower variance is better (more authentic)
        max_expected_variance = 5000  # Tuning parameter
        normalized = min(1.0, variance / max_expected_variance)
        
        # Invert so higher score = more authentic
        score = 1.0 - normalized
        
        return score
    
    def _find_suspicious_regions(
        self, 
        amplified: 'np.ndarray'
    ) -> List[Tuple[int, int, int, int]]:
        """Find regions with unusually high error levels."""
        if amplified is None or not HAS_IMAGING:
            return []
        
        regions = []
        
        # Simple threshold-based detection
        mean_val = np.mean(amplified)
        threshold = mean_val + (np.std(amplified) * 2)
        
        # Find pixels above threshold
        bright_pixels = np.where(np.mean(amplified, axis=2) > threshold)
        
        if len(bright_pixels[0]) > 0:
            # Create bounding box
            y_min, y_max = int(np.min(bright_pixels[0])), int(np.max(bright_pixels[0]))
            x_min, x_max = int(np.min(bright_pixels[1])), int(np.max(bright_pixels[1]))
            
            if (y_max - y_min) > 10 and (x_max - x_min) > 10:
                regions.append((x_min, y_min, x_max - x_min, y_max - y_min))
        
        return regions
    
    def _create_ela_image(self, amplified: 'np.ndarray') -> Optional[bytes]:
        """Create a visual ELA image for display."""
        if amplified is None or not HAS_IMAGING:
            return None
        
        try:
            ela_img = Image.fromarray(amplified.astype(np.uint8))
            buffer = io.BytesIO()
            ela_img.save(buffer, format='PNG')
            return buffer.getvalue()
        except Exception:
            return None


class ForensicEngine:
    """
    Orchestrates forensic analysis by combining metadata and ELA analysis.
    
    This is the main entry point for forensic verification of submitted evidence.
    """
    
    def __init__(
        self,
        ela_quality: int = 90,
        ela_amplification: int = 50
    ):
        """
        Initialize the forensic engine with analyzers.
        
        Args:
            ela_quality: JPEG quality for ELA (default 90)
            ela_amplification: ELA amplification factor (default 50)
        """
        self._metadata_analyzer = MetadataAnalyzer()
        self._ela_processor = ELAProcessor(
            resave_quality=ela_quality,
            amplification_factor=ela_amplification
        )
        self._analysis_count = 0
    
    @property
    def metadata_analyzer(self) -> MetadataAnalyzer:
        """Get the metadata analyzer instance."""
        return self._metadata_analyzer
    
    @property
    def ela_processor(self) -> ELAProcessor:
        """Get the ELA processor instance."""
        return self._ela_processor
    
    def analyze_evidence(self, image_data: bytes) -> ForensicResult:
        """
        Perform complete forensic analysis on submitted evidence.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            ForensicResult with all analysis scores
        """
        self._analysis_count += 1
        
        flags = []
        
        # Generate image hash for duplicate detection
        image_hash = self._generate_hash(image_data)
        
        # Perform metadata analysis
        try:
            metadata_score, metadata_details = self._metadata_analyzer.analyze(image_data)
            
            if metadata_details.get("is_suspicious"):
                flags.append("SUSPICIOUS_SOFTWARE_DETECTED")
            if not metadata_details.get("has_metadata"):
                flags.append("METADATA_STRIPPED")
                
        except Exception as e:
            metadata_score = 0.5
            metadata_details = {"error": str(e)}
            flags.append("METADATA_ANALYSIS_FAILED")
        
        # Perform ELA
        try:
            ela_result = self._ela_processor.perform_ela(image_data)
            ela_score = ela_result.variance_score
            
            if len(ela_result.suspicious_regions) > 0:
                flags.append("SUSPICIOUS_REGIONS_DETECTED")
                
        except Exception as e:
            ela_score = 0.5
            ela_result = None
            flags.append("ELA_ANALYSIS_FAILED")
        
        # Determine overall status
        if "FAILED" in " ".join(flags):
            status = AnalysisStatus.FAILED
        elif not flags:
            status = AnalysisStatus.COMPLETED
        else:
            status = AnalysisStatus.COMPLETED
        
        # Compile details
        details = {
            "metadata": metadata_details,
            "ela": {
                "variance_score": ela_result.variance_score if ela_result else None,
                "max_difference": ela_result.max_difference if ela_result else None,
                "mean_difference": ela_result.mean_difference if ela_result else None,
                "suspicious_region_count": len(ela_result.suspicious_regions) if ela_result else 0
            }
        }
        
        return ForensicResult(
            metadata_score=metadata_score,
            ela_score=ela_score,
            image_hash=image_hash,
            status=status,
            flags=flags,
            details=details
        )
    
    def run_full_scan(self, image_data: bytes) -> Tuple[float, float]:
        """
        Quick scan returning only metadata and ELA scores.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Tuple of (metadata_score, ela_score)
        """
        result = self.analyze_evidence(image_data)
        return (result.metadata_score, result.ela_score)
    
    def _generate_hash(self, image_data: bytes) -> str:
        """Generate SHA-256 hash of image data."""
        return hashlib.sha256(image_data).hexdigest()


# Example usage and demonstration
if __name__ == "__main__":
    print("=" * 60)
    print("VeriSupport Forensic Analysis Engine - Demo")
    print("=" * 60)
    
    # Initialize engine
    engine = ForensicEngine()
    
    print(f"\n[OK] ForensicEngine initialized")
    print(f"    - MetadataAnalyzer: Ready")
    print(f"    - ELAProcessor: Ready (quality={engine.ela_processor.resave_quality}%, "
          f"amplification={engine.ela_processor.amplification_factor}x)")
    
    # Demo with synthetic test data
    print("\n[*] Running demo with test data...")
    
    # Create a simple test image
    if HAS_IMAGING:
        test_img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG', quality=95)
        test_data = buffer.getvalue()
        
        # Analyze
        result = engine.analyze_evidence(test_data)
        
        print(f"\n[RESULT] Forensic Analysis Complete")
        print(f"    - Status: {result.status.value}")
        print(f"    - Image Hash: {result.image_hash[:16]}...")
        print(f"    - Metadata Score: {result.metadata_score}")
        print(f"    - ELA Score: {result.ela_score:.2f}")
        print(f"    - Flags: {result.flags if result.flags else 'None'}")
    else:
        print("    [!] Imaging libraries not available for demo")
    
    print("\n" + "=" * 60)
    print("Module loaded successfully!")
    print("=" * 60)
