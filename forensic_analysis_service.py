"""
VeriSupport — Forensic Analysis Service (Microservice)

This microservice handles forensic image analysis for the VeriSupport platform.
It runs as an independent service, consuming evidence images from a message queue,
performing EXIF metadata analysis and Error Level Analysis (ELA), and publishing
forensic scores back to the decision queue.

Components:
    - MetadataAnalyzer: Parses EXIF data, detects suspicious software signatures
    - ELAProcessor: Performs Error Level Analysis for compression artifact detection
    - ForensicEngine: Orchestrates both analyses and produces a unified result

Author: VeriSupport Team
Assignment: 5 — CS 331 Software Engineering Lab
"""

import hashlib
import io
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple
from enum import Enum
from datetime import datetime

# Optional imports for image processing
try:
    from PIL import Image, ImageChops
    import numpy as np
    HAS_IMAGING = True
except ImportError:
    HAS_IMAGING = False


# ────────────────────────────────────────────────────────────────────
# Data Classes
# ────────────────────────────────────────────────────────────────────

class AnalysisStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExifData:
    """Container for extracted EXIF metadata."""
    make: Optional[str] = None
    model: Optional[str] = None
    software: Optional[str] = None
    datetime_original: Optional[str] = None
    has_thumbnail: bool = False
    raw_data: Optional[Dict] = None


@dataclass
class ELAResult:
    """Result of Error Level Analysis."""
    variance_score: float
    max_difference: float
    mean_difference: float
    suspicious_regions: List[Tuple[int, int, int, int]]


@dataclass
class ForensicResult:
    """Combined result of all forensic analyses."""
    metadata_score: float       # 0.0 or 1.0 (binary)
    ela_score: float            # 0.0 - 1.0 (normalized)
    image_hash: str
    status: str
    flags: List[str]
    details: Dict
    timestamp: str


# ────────────────────────────────────────────────────────────────────
# MetadataAnalyzer
# ────────────────────────────────────────────────────────────────────

class MetadataAnalyzer:
    """
    Analyzes image metadata (EXIF) to detect potential manipulation.

    Checks for:
      - Software signatures (Adobe, GIMP, Stable Diffusion, etc.)
      - Missing or stripped metadata
      - Inconsistent camera fields
    """

    SUSPICIOUS_SOFTWARE: List[str] = [
        "adobe", "photoshop", "gimp", "canva", "pixlr",
        "stable diffusion", "midjourney", "dall-e", "dalle",
        "figma", "sketch", "affinity", "paint.net", "lightroom",
        "illustrator", "inpaint", "remove.bg", "photoroom"
    ]

    def __init__(self):
        self._analysis_count = 0

    def extract_exif(self, image_data: bytes) -> ExifData:
        """Extract EXIF metadata from image bytes."""
        if not HAS_IMAGING:
            return ExifData(raw_data={"error": "Imaging library not available"})
        try:
            img = Image.open(io.BytesIO(image_data))
            exif_dict = {}
            if hasattr(img, '_getexif') and img._getexif():
                exif_dict = img._getexif()
            return ExifData(
                make=exif_dict.get(271),
                model=exif_dict.get(272),
                software=exif_dict.get(305),
                datetime_original=exif_dict.get(36867),
                has_thumbnail='thumbnail' in str(img.info).lower(),
                raw_data=exif_dict if exif_dict else None
            )
        except Exception as e:
            return ExifData(raw_data={"error": str(e)})

    def detect_software_signatures(self, exif: ExifData) -> Tuple[bool, List[str]]:
        """Detect suspicious software signatures in EXIF data."""
        detected = []
        if exif.software:
            for suspicious in self.SUSPICIOUS_SOFTWARE:
                if suspicious in exif.software.lower():
                    detected.append(exif.software)
                    break
        if exif.raw_data and not isinstance(exif.raw_data.get("error"), str):
            raw_str = str(exif.raw_data).lower()
            for suspicious in self.SUSPICIOUS_SOFTWARE:
                if suspicious in raw_str and suspicious not in [d.lower() for d in detected]:
                    detected.append(suspicious)
        return (len(detected) > 0, detected)

    def validate_source(self, exif: ExifData) -> float:
        """Validate if the image is from an authentic camera source. Returns 0.0-1.0."""
        score = 0.5
        if exif.make and exif.model:
            score += 0.3
        if exif.datetime_original:
            score += 0.2
        is_suspicious, _ = self.detect_software_signatures(exif)
        if is_suspicious:
            score = 0.0
        if not exif.raw_data or (isinstance(exif.raw_data, dict) and exif.raw_data.get("error")):
            score = max(0.0, score - 0.3)
        return min(1.0, max(0.0, score))

    def analyze(self, image_data: bytes) -> Tuple[float, Dict]:
        """Perform complete metadata analysis. Returns (score, details)."""
        self._analysis_count += 1
        exif = self.extract_exif(image_data)
        is_suspicious, detected_software = self.detect_software_signatures(exif)
        source_score = self.validate_source(exif)

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


# ────────────────────────────────────────────────────────────────────
# ELAProcessor
# ────────────────────────────────────────────────────────────────────

class ELAProcessor:
    """
    Performs Error Level Analysis (ELA) to detect image manipulation.

    ELA works by:
      1. Resaving the image at a known quality (90%)
      2. Calculating pixel differences between original and resaved
      3. Amplifying these differences (x50)
      4. Authentic images show uniform noise; manipulated regions glow
    """

    def __init__(self, resave_quality: int = 90, amplification_factor: int = 50):
        self._resave_quality = resave_quality
        self._amplification_factor = amplification_factor

    @property
    def resave_quality(self) -> int:
        return self._resave_quality

    @property
    def amplification_factor(self) -> int:
        return self._amplification_factor

    def perform_ela(self, image_data: bytes) -> ELAResult:
        """Perform Error Level Analysis on an image."""
        if not HAS_IMAGING:
            return ELAResult(variance_score=0.5, max_difference=0,
                             mean_difference=0, suspicious_regions=[])
        try:
            original = Image.open(io.BytesIO(image_data))
            if original.mode != 'RGB':
                original = original.convert('RGB')
            buffer = io.BytesIO()
            original.save(buffer, format='JPEG', quality=self._resave_quality)
            buffer.seek(0)
            resaved = Image.open(buffer)

            diff = ImageChops.difference(original, resaved)
            diff_array = np.array(diff, dtype=np.float32)
            amplified = np.clip(diff_array * self._amplification_factor, 0, 255)

            variance = np.var(amplified)
            normalized = min(1.0, variance / 5000)
            variance_score = 1.0 - normalized

            max_diff = float(np.max(amplified))
            mean_diff = float(np.mean(amplified))

            suspicious_regions = self._find_suspicious_regions(amplified)
            return ELAResult(
                variance_score=variance_score,
                max_difference=max_diff,
                mean_difference=mean_diff,
                suspicious_regions=suspicious_regions
            )
        except Exception:
            return ELAResult(variance_score=0.5, max_difference=0,
                             mean_difference=0, suspicious_regions=[])

    def _find_suspicious_regions(self, amplified) -> List[Tuple[int, int, int, int]]:
        regions = []
        mean_val = np.mean(amplified)
        threshold = mean_val + (np.std(amplified) * 2)
        bright_pixels = np.where(np.mean(amplified, axis=2) > threshold)
        if len(bright_pixels[0]) > 0:
            y_min, y_max = int(np.min(bright_pixels[0])), int(np.max(bright_pixels[0]))
            x_min, x_max = int(np.min(bright_pixels[1])), int(np.max(bright_pixels[1]))
            if (y_max - y_min) > 10 and (x_max - x_min) > 10:
                regions.append((x_min, y_min, x_max - x_min, y_max - y_min))
        return regions


# ────────────────────────────────────────────────────────────────────
# ForensicEngine (Orchestrator)
# ────────────────────────────────────────────────────────────────────

class ForensicEngine:
    """
    Orchestrates forensic analysis by combining MetadataAnalyzer and ELAProcessor.
    This is the main entry point for the Forensic Analysis Service.
    """

    def __init__(self, ela_quality: int = 90, ela_amplification: int = 50):
        self._metadata_analyzer = MetadataAnalyzer()
        self._ela_processor = ELAProcessor(
            resave_quality=ela_quality,
            amplification_factor=ela_amplification
        )

    @property
    def metadata_analyzer(self) -> MetadataAnalyzer:
        return self._metadata_analyzer

    @property
    def ela_processor(self) -> ELAProcessor:
        return self._ela_processor

    def analyze_evidence(self, image_data: bytes) -> ForensicResult:
        """Perform complete forensic analysis on submitted evidence."""
        flags = []
        image_hash = hashlib.sha256(image_data).hexdigest()

        # Metadata Analysis
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

        # ELA Analysis
        try:
            ela_result = self._ela_processor.perform_ela(image_data)
            ela_score = ela_result.variance_score
            if len(ela_result.suspicious_regions) > 0:
                flags.append("SUSPICIOUS_REGIONS_DETECTED")
        except Exception:
            ela_score = 0.5
            ela_result = None
            flags.append("ELA_ANALYSIS_FAILED")

        status = "failed" if "FAILED" in " ".join(flags) else "completed"

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
            details=details,
            timestamp=datetime.now().isoformat()
        )


# ────────────────────────────────────────────────────────────────────
# Service API (simulates FastAPI endpoints for the microservice)
# ────────────────────────────────────────────────────────────────────

class ForensicAnalysisService:
    """
    Microservice wrapper around ForensicEngine.

    In production, this would be a FastAPI app running on port 8002,
    consuming from forensic_analysis_queue (RabbitMQ) and publishing
    results to decision_queue.
    """

    def __init__(self):
        self.engine = ForensicEngine()
        self.service_name = "forensic-analysis-service"
        self.port = 8002

    def health_check(self) -> Dict:
        """GET /health — Liveness probe."""
        return {"status": "healthy", "service": self.service_name, "port": self.port}

    def analyze(self, image_data: bytes, dispute_id: str) -> Dict:
        """
        POST /analyze — Main analysis endpoint.

        In production, this would consume from forensic_analysis_queue
        and publish results to decision_queue.
        """
        print(f"  [{self.service_name}] Analyzing evidence for dispute: {dispute_id}")

        result = self.engine.analyze_evidence(image_data)

        response = {
            "service": self.service_name,
            "dispute_id": dispute_id,
            "metadata_score": result.metadata_score,
            "ela_score": result.ela_score,
            "image_hash": result.image_hash,
            "status": result.status,
            "flags": result.flags,
            "timestamp": result.timestamp
        }

        print(f"  [{self.service_name}] Analysis complete:")
        print(f"    - Metadata Score (S_meta): {result.metadata_score}")
        print(f"    - ELA Score (S_ela):       {result.ela_score:.4f}")
        print(f"    - Flags: {result.flags if result.flags else 'None'}")

        return response


# ────────────────────────────────────────────────────────────────────
# Standalone Demo
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("  VeriSupport — Forensic Analysis Service (Microservice)")

    service = ForensicAnalysisService()

    # Health check
    health = service.health_check()
    print(f"\n  Health Check: {health}")

    # Create a test image
    if HAS_IMAGING:
        test_img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        test_img.save(buffer, format='JPEG', quality=95)
        test_data = buffer.getvalue()

        result = service.analyze(test_data, "DEMO-001")
        print(f"\n  Result: {json.dumps(result, indent=2, default=lambda o: float(o) if hasattr(o, 'item') else str(o))}")
    else:
        print("\n  [!] PIL/numpy not installed. Run: pip install Pillow numpy")

    print("\n  Service module loaded successfully!")
