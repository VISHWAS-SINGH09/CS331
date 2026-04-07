# Software Requirements Specification (SRS)
Project: AI-based Customer Support Automation Platform with Digital Image Forensics

## 1. Abstract
The rapid adoption of Generative AI has introduced "Adversarial Refund Fraud" in the E-Commerce and Food Delivery sectors. VeriSupport is a novel Customer Support Automation Platform that integrates Multimodal Large Language Models (LLMs) with Digital Image Forensics. It acts as an "Active Defense" mechanism, utilizing Error Level Analysis (ELA), Metadata Scrutiny, and Vision-Language reasoning to autonomously verify the physical integrity of user claims in real-time. The goal is to reduce refund processing latency for genuine customers while neutralizing AI-generated fraud.

## 2. Problem Statement
The system addresses three critical vulnerabilities in current support infrastructure:
1.  **Vulnerability to Synthetic Media:** Existing systems cannot distinguish between authentic photographs and AI-generated or digitally manipulated images.
2.  **Inefficient Triage:** Genuine disputes often face resolution times of 24-48 hours due to the need for manual human review.
3.  **Revenue Leakage:** Companies suffer financial losses due to fraudsters exploiting "no-questions-asked" refund policies using manipulated media.

## 3. Novelty & Innovation (Technical Differentiators)
VeriSupport introduces an "Adversarial Defense Framework" with the following key features:
* **Cryptographic & Forensic Gatekeeping:** Implements pixel-level forensic analysis (Error Level Analysis) before processing support tickets.
* **Live-Constraint Enforcement:** Enforces a "Live-Only" capture mode using HTML5 hardware constraints to disable file system uploads, countering PC-based editing tools.
* **Weighted Ensemble Decision Logic:** Uses a probabilistic approach combining metadata, compression artifacts, and semantic consistency into a single confidence metric.

## 4. Functional Requirements (FR)

### Module 1: The User Interaction & Evidence Interface
* **FR 1.1:** The system shall provide a conversational chat interface capable of collecting context regarding the dispute.
* **FR 1.2:** The system shall enforce Real-Time Image Capture, programmatically disabling "Upload from Gallery" to prevent submission of pre-edited images.

### Module 2: The Forensic Analysis Engine (Microscopic Check)
* **FR 2.1 (Metadata Scrutiny):** The system shall parse EXIF data to validate the source device. Images containing software signatures (e.g., "Adobe", "Stable Diffusion") must be flagged.
* **FR 2.2 (Error Level Analysis - ELA):** The system shall perform a microscopic pixel-level scan to detect JPEG Compression Artifacts.
    * **Algorithm:** The system creates a control image by resaving the input at 90% quality and calculates the pixel difference: `Difference = |Pixel_A - Pixel_B|`.
    * **Amplification:** This difference is multiplied by a scaling factor (x50) to make manipulated regions visible.

### Module 3: The AI Reasoning Agent
* **FR 3.1:** The system shall utilize a Vision-Language Model (Gemini 1.5 Flash) to perform Semantic Consistency Checks (e.g., verifying if text descriptions match visual data).

### Module 4: Decision Algorithm (The Mathematical Core)
* **FR 4.1:** The system shall compute the final Trust Score ($T$) using a weighted ensemble algorithm:
    $$T=w_1(S_{meta})+w_2(S_{ela})+w_3(S_{ai})$$
    * $S_{meta}$: Binary score (0 or 1) based on EXIF validity.
    * $S_{ela}$: Normalized score inversely proportional to error level variance.
    * $S_{ai}$: Confidence score from the Vision-Language Model.
* **FR 4.2:** If $T > 0.9$, the system shall trigger the Auto-Refund API.
* **FR 4.3:** If $T < 0.5$, the system shall route the ticket to a human agent with a "Fraud Alert" tag.

## 5. Non-Functional Requirements (NFR)
* **NFR 1 (Latency):** The complete forensic audit (Metadata + ELA + AI Analysis) must complete within 5 seconds.
* **NFR 2 (Scalability):** The backend must utilize serverless architecture (FastAPI/Lambda) to handle concurrent requests.
* **NFR 3 (Privacy):** User images must be processed in ephemeral memory and permanently deleted post-resolution unless archived for confirmed fraud.

## 6. Technology Stack
* **Frontend:** Streamlit / React.js (with HTML5 Media Capture API).
* **Backend:** Python 3.x (FastAPI).
* **AI Models:** Google Gemini 1.5 Flash.
* **Forensics:** OpenCV, Pillow (PIL), ExifRead.
* **Database:** Supabase (PostgreSQL), Pinecone (Vector DB).

## 7. Evaluation Methodology
The system will be stress-tested using a "Red Teaming" approach with 50 adversarial images generated via:
1.  **Generative Fill Attack:** Adding foreign objects via Photoshop.
2.  **Inpainting Attack:** Erasing/replacing items via Stable Diffusion.
3.  **Metadata Scrubbing:** Programmatically stripping EXIF data.

**Scoring Metrics:**
* **True Positive:** Correctly flagging "FRAUD".
* **False Negative:** Incorrectly granting "REFUND APPROVED".
* **Robustness Score:** Calculated as the Recall Rate.
