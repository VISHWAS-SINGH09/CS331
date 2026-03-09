"""
VeriSupport — End-to-End Microservice Interaction Demo

This script demonstrates the interaction between two core microservices:
  1. Forensic Analysis Service  (MetadataAnalyzer + ELAProcessor + ForensicEngine)
  2. Decision Engine Service    (TrustScoreCalculator + DecisionRouter)

The services communicate via a simulated message queue. Three scenarios are
processed to show all three decision outcomes: Auto-Refund, Fraud Alert,
and Manual Review.

Usage:
    python run_demo.py

Author: VeriSupport Team
Assignment: 5 — CS 331 Software Engineering Lab
"""

import sys
import os
import io
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forensic_analysis_service import ForensicAnalysisService
from decision_engine_service import DecisionEngineService

# Optional: PIL for creating test images
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ────────────────────────────────────────────────────────────────────
# Simulated Message Queue
# ────────────────────────────────────────────────────────────────────

class SimulatedMessageQueue:
    """
    Simulates RabbitMQ / Redis message queue for inter-service communication.

    In production, this would be replaced by:
      - CloudAMQP (managed RabbitMQ)
      - Redis Streams
      - AWS SQS
    """

    def __init__(self):
        self.queues = {
            "forensic_analysis_queue": [],
            "ai_reasoning_queue": [],
            "decision_queue": [],
            "notification_queue": []
        }

    def publish(self, queue_name: str, message: dict):
        """Publish a message to a queue."""
        self.queues[queue_name].append(message)
        print(f"    [MQ] Published to '{queue_name}': dispute_id={message.get('dispute_id', 'N/A')}")

    def consume(self, queue_name: str) -> dict:
        """Consume a message from a queue."""
        if self.queues[queue_name]:
            msg = self.queues[queue_name].pop(0)
            print(f"    [MQ] Consumed from '{queue_name}': dispute_id={msg.get('dispute_id', 'N/A')}")
            return msg
        return None


# ────────────────────────────────────────────────────────────────────
# Test Image Generator
# ────────────────────────────────────────────────────────────────────

def create_test_image(color='blue', size=(200, 200)) -> bytes:
    """Create a simple test image in JPEG format."""
    if not HAS_PIL:
        # Return minimal JPEG bytes if PIL not available
        return b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9'
    img = Image.new('RGB', size, color=color)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    return buffer.getvalue()


# ────────────────────────────────────────────────────────────────────
# Main Demo
# ────────────────────────────────────────────────────────────────────

def run_demo():
    print()
    print("=" * 72)
    print("  VeriSupport -- Microservice Interaction Demo")
    print("  Assignment 5 -- CS 331 Software Engineering Lab")
    print("=" * 72)

    # ── Initialize services ─────────────────────────────────────────
    print("\n  [1/4] Initializing Microservices...")
    print("  " + "-" * 50)

    forensic_service = ForensicAnalysisService()
    decision_service = DecisionEngineService()
    message_queue = SimulatedMessageQueue()

    print(f"  [OK] {forensic_service.service_name} (port {forensic_service.port})")
    print(f"  [OK] {decision_service.service_name} (port {decision_service.port})")
    print(f"  [OK] Message Queue (simulated RabbitMQ)")

    # ── Health Checks ───────────────────────────────────────────────
    print("\n  [2/4] Running Health Checks...")
    print("  " + "-" * 50)

    for svc in [forensic_service, decision_service]:
        health = svc.health_check()
        status = "[OK] HEALTHY" if health["status"] == "healthy" else "[FAIL] UNHEALTHY"
        print(f"  {status} — {health['service']} on port {health['port']}")

    # ── Test Scenarios ──────────────────────────────────────────────
    print("\n  [3/4] Processing Dispute Scenarios...")
    print("  " + "-" * 50)

    scenarios = [
        {
            "name": "Authentic Image (Clean Camera Photo)",
            "dispute_id": "DISP-AUTH-20260308-001",
            "description": "Genuine photo from iPhone camera, no editing software",
            "image_color": "green",
            "simulated_ai_score": 0.92,
            "user_email": "alice@example.com",
            "order_amount": 49.99,
            # For this demo, since we use synthetic images (no real EXIF),
            # we simulate known scores to show all three decision paths.
            "simulated_meta_score": 1.0,
            "simulated_ela_score": 0.95,
            "expected_decision": "AUTO-REFUND (T > 0.9)"
        },
        {
            "name": "Manipulated Image (Photoshop Detected)",
            "dispute_id": "DISP-FRAD-20260308-002",
            "description": "Image edited with Adobe Photoshop, high ELA variance",
            "image_color": "red",
            "simulated_ai_score": 0.25,
            "user_email": "bob@example.com",
            "order_amount": 199.99,
            "simulated_meta_score": 0.0,
            "simulated_ela_score": 0.30,
            "expected_decision": "FRAUD ALERT (T < 0.5)"
        },
        {
            "name": "Borderline Case (Stripped Metadata)",
            "dispute_id": "DISP-EDGE-20260308-003",
            "description": "Metadata stripped but no editing software, partial AI match",
            "image_color": "yellow",
            "simulated_ai_score": 0.65,
            "user_email": "carol@example.com",
            "order_amount": 29.99,
            "simulated_meta_score": 0.0,
            "simulated_ela_score": 0.72,
            "expected_decision": "MANUAL REVIEW (0.5 <= T <= 0.9)"
        }
    ]

    results = []

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n  {'=' * 68}")
        print(f"  | SCENARIO {i}: {scenario['name']}")
        print(f"  | {scenario['description']}")
        print(f"  | Expected: {scenario['expected_decision']}")
        print(f"  {'=' * 68}")

        # Step A: Generate test evidence
        image_data = create_test_image(color=scenario["image_color"])
        print(f"\n  [A] Evidence submitted ({len(image_data)} bytes)")

        # Step B: Forensic Analysis Service processes the image
        print(f"\n  [B] Forensic Analysis Service processing...")
        forensic_result = forensic_service.analyze(image_data, scenario["dispute_id"])

        # In demo mode, use simulated scores for consistent demonstration
        meta_score = scenario["simulated_meta_score"]
        ela_score = scenario["simulated_ela_score"]
        ai_score = scenario["simulated_ai_score"]

        print(f"\n  [B'] Using scenario scores for demo:")
        print(f"    S_meta = {meta_score} (Metadata)")
        print(f"    S_ela  = {ela_score} (ELA)")
        print(f"    S_ai   = {ai_score} (AI Semantic)")

        # Step C: Publish scores to message queue
        print(f"\n  [C] Publishing to message queue...")
        message_queue.publish("decision_queue", {
            "dispute_id": scenario["dispute_id"],
            "metadata_score": meta_score,
            "ela_score": ela_score,
            "ai_score": ai_score,
            "user_email": scenario["user_email"],
            "order_amount": scenario["order_amount"]
        })

        # Step D: Decision Engine Service consumes and processes
        print(f"\n  [D] Decision Engine Service consuming & processing...")
        queue_msg = message_queue.consume("decision_queue")

        decision_result = decision_service.process_scores(
            dispute_id=queue_msg["dispute_id"],
            metadata_score=queue_msg["metadata_score"],
            ela_score=queue_msg["ela_score"],
            ai_score=queue_msg["ai_score"],
            user_email=queue_msg["user_email"],
            order_amount=queue_msg["order_amount"]
        )

        results.append({
            "scenario": scenario["name"],
            "trust_score": decision_result["trust_score"],
            "decision": decision_result["decision"],
            "action": decision_result["action_taken"]
        })

    # ── Summary ─────────────────────────────────────────────────────
    print(f"\n\n  [4/4] Results Summary")
    print("  " + "=" * 68)
    print(f"  {'Scenario':<42} {'Trust Score':>12} {'Decision':>14}")
    print("  " + "-" * 68)

    decision_icons = {
        "auto_refund": "[PASS]",
        "fraud_alert": "[ALERT]",
        "manual_review": "[REVIEW]"
    }

    for r in results:
        icon = decision_icons.get(r["decision"], "[?]")
        dec_display = r["decision"].upper().replace("_", " ")
        print(f"  {r['scenario']:<42} {r['trust_score']:>10.4f}   {icon} {dec_display}")

    print("  " + "=" * 68)

    print(f"""
  Formula: T = 0.20 * S_meta + 0.35 * S_ela + 0.45 * S_ai

  Decision Thresholds:
    T > 0.9   -->  AUTO-REFUND    (process refund, notify user)
    T < 0.5   -->  FRAUD ALERT    (alert agent, flag dispute)
    otherwise -->  MANUAL REVIEW  (queue for human review)
    """)

    print("=" * 72)
    print("  Demo completed successfully!")
    print("  All microservice interactions demonstrated.")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
