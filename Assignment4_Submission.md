# Assignment 4 Submission
## CS 331 Software Engineering Lab
## VeriSupport: Autonomous Multimodal Customer Support & Forensic Integrity System

---

# I. Software Architecture Style

## Chosen Architecture: Layered (N-Tier) Architecture

VeriSupport follows a **Layered (N-Tier) Architecture** organized into four distinct horizontal layers. Each layer has a well-defined responsibility and communicates only with its immediate neighbor, enforcing a strict separation of concerns.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                          LAYER 1 — PRESENTATION LAYER                            │
│                                                                                   │
│   ┌────────────────────┐   ┌─────────────────────┐   ┌────────────────────────┐  │
│   │  Streamlit / React │   │  HTML5 Media Capture │   │   Admin Dashboard UI   │  │
│   │   Chat Interface   │   │   (Live Camera)      │   │   (Analytics Views)    │  │
│   └────────────────────┘   └─────────────────────┘   └────────────────────────┘  │
│                                                                                   │
├───────────────────────────────────────────────────────────────────────────────────┤
│                          LAYER 2 — APPLICATION / API LAYER                       │
│                                                                                   │
│   ┌────────────────────┐   ┌─────────────────────┐   ┌────────────────────────┐  │
│   │  FastAPI Endpoints │   │  Authentication      │   │  Session Management    │  │
│   │  (REST Routes)     │   │  Middleware          │   │  & Rate Limiting       │  │
│   └────────────────────┘   └─────────────────────┘   └────────────────────────┘  │
│                                                                                   │
├───────────────────────────────────────────────────────────────────────────────────┤
│                          LAYER 3 — BUSINESS LOGIC LAYER                          │
│                                                                                   │
│   ┌─────────────────┐  ┌────────────────┐  ┌───────────────┐  ┌──────────────┐  │
│   │ ForensicEngine  │  │ TrustScore     │  │ DecisionRouter│  │ AISemantic   │  │
│   │  ├MetadataAnalyzer│ │ Calculator    │  │               │  │ Checker      │  │
│   │  └ELAProcessor  │  │               │  │               │  │ (Gemini API) │  │
│   └─────────────────┘  └────────────────┘  └───────────────┘  └──────────────┘  │
│                                                                                   │
├───────────────────────────────────────────────────────────────────────────────────┤
│                          LAYER 4 — DATA / PERSISTENCE LAYER                      │
│                                                                                   │
│   ┌────────────────────┐   ┌─────────────────────┐   ┌────────────────────────┐  │
│   │  Supabase          │   │  Pinecone            │   │  Evidence Archive      │  │
│   │  (PostgreSQL)      │   │  (Vector DB)         │   │  (Hashed Images)       │  │
│   └────────────────────┘   └─────────────────────┘   └────────────────────────┘  │
│                                                                                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

### A. Justification by Component Granularity

The Layered Architecture is justified because every VeriSupport component naturally falls into one of the four layers, with clear boundaries and no cross-layer leakage.

| Layer | Granularity | Components | Responsibility |
|-------|-------------|------------|----------------|
| **Presentation** | Coarse-grained UI modules | Streamlit/React chat interface, HTML5 Media Capture widget, Admin Dashboard | Rendering views, collecting user input (dispute text + live images), displaying results |
| **Application / API** | Medium-grained route handlers | FastAPI REST endpoints (`/submit-dispute`, `/check-status`, `/admin/analytics`), Auth middleware, Session manager | Request validation, authentication, routing HTTP calls to the business logic layer |
| **Business Logic** | Fine-grained domain classes | `ForensicEngine`, `MetadataAnalyzer`, `ELAProcessor`, `AISemanticChecker`, `TrustScoreCalculator`, `DecisionRouter`, `ScoreWeights` | Core algorithms — EXIF parsing, ELA computation, Gemini API calls, weighted trust scoring, decision routing |
| **Data / Persistence** | Coarse-grained data stores | Supabase PostgreSQL (User DB, Transaction Logs), Pinecone Vector DB (duplicate detection), Evidence Archive (hashed images + metadata) | CRUD operations, query execution, image storage, vector similarity search |

**Mapping of UML Classes (from Assignment 3) to Layers:**

| UML Class | Layer | Rationale |
|-----------|-------|-----------|
| `RegisteredUser`, `SupportAgent`, `SystemAdmin` (User hierarchy) | Presentation + Data | User models are persisted in the Data layer; their UI interactions happen in the Presentation layer |
| `RefundDispute`, `Evidence` | Business Logic + Data | Domain entities processed by business rules and persisted in transaction logs |
| `ForensicEngine` | Business Logic | Orchestrates `MetadataAnalyzer` and `ELAProcessor` — pure analysis logic |
| `MetadataAnalyzer` | Business Logic | EXIF parsing and software signature detection — domain-specific algorithm |
| `ELAProcessor` | Business Logic | Pixel-level compression analysis — domain-specific algorithm |
| `AISemanticChecker` | Business Logic | Bridges to Gemini 1.5 API for semantic consistency — encapsulated service call |
| `TrustScoreCalculator` | Business Logic | Implements `T = w₁(S_meta) + w₂(S_ela) + w₃(S_ai)` — core decision math |
| `DecisionRouter` | Business Logic | Routes decisions (auto-refund / manual review / fraud alert) |
| `ScoreWeights` | Business Logic | Configuration data class consumed by `TrustScoreCalculator` |
| `RefundAPI` (interface) | Application | External banking integration, called by `DecisionRouter` through the API layer |
| `NotificationService` (interface) | Application | Email / SMS / Push delivery, abstracted behind an interface |

This mapping demonstrates that VeriSupport's component granularity naturally segments into **layers**, not into independently deployable services (ruling out Microservices) or a single monolith (ruling out Monolithic).

---

### B. Why Layered Architecture is the Best Choice

#### 1. Scalability
- **Horizontal scaling at the API layer**: FastAPI can be deployed behind a load balancer on serverless platforms (AWS Lambda / Cloud Run), satisfying **NFR 2** (serverless scalability). Each layer scales independently — the stateless API layer can auto-scale without affecting the business logic or data layer.
- **No inter-service network overhead**: Unlike Microservices, Layered Architecture avoids the latency cost of network calls between services, which is critical for meeting **NFR 1** (< 5 seconds for the full forensic audit pipeline).

#### 2. Maintainability
- **Separation of concerns**: Changes to the frontend (e.g., migrating from Streamlit to React) do not affect the `ForensicEngine` or `TrustScoreCalculator`. Similarly, updating the ELA algorithm only requires modifying `ELAProcessor` within the Business Logic layer.
- **Testability**: Each layer can be unit-tested in isolation. Assignment 3 already demonstrated this — `ForensicEngine` and `TrustScoreCalculator` were tested independently with no dependency on the Presentation or Data layers.
- **Clear dependency direction**: Dependencies flow **downward only** (Presentation → API → Business Logic → Data), preventing circular dependencies and simplifying debugging.

#### 3. Performance
- **In-process function calls**: The Business Logic layer components (`ForensicEngine` → `MetadataAnalyzer` → `ELAProcessor` → `TrustScoreCalculator` → `DecisionRouter`) communicate via direct Python function calls, not network requests. This minimizes latency for the time-critical forensic analysis pipeline.
- **Ephemeral image processing** (**NFR 3**): The Business Logic layer processes images in-memory and passes only scores to the Data layer, ensuring user images are never unnecessarily persisted.

#### 4. Team Development
- **Parallel development**: Frontend developers work on the Presentation layer, backend developers on the API layer, ML/forensics engineers on the Business Logic layer, and DBAs on the Data layer — all simultaneously with minimal merge conflicts.
- **Clear API contracts**: The API layer defines REST endpoints that serve as contracts between the frontend and backend teams.

#### 5. Why Not Other Architectures?

| Architecture | Why Not Suitable |
|-------------|-----------------|
| **Microservices** | Adds unnecessary operational complexity (service discovery, inter-service communication, distributed tracing) for a system with tightly coupled forensic analysis steps that must execute sequentially within 5 seconds. The overhead of network hops between ForensicEngine, TrustScoreCalculator, and DecisionRouter would violate the latency NFR. |
| **Monolithic** | While simple, a pure monolith bundles the UI, API, and database into a single deployable unit, making it difficult to scale the API layer independently or replace the frontend framework without a full redeploy. |
| **Service-Oriented (SOA)** | SOA's enterprise service bus and WSDL contracts are over-engineered for a project of this scope. The communication overhead and governance model are disproportionate to VeriSupport's needs. |

---

# II. Application Components

The following table lists all application components present in the VeriSupport system, organized by subsystem.

## Component Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VERISUPPORT PLATFORM                           │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  FRONTEND COMPONENTS                                                 │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │   │
│  │  │ Chat UI      │  │ Camera Module │  │ Admin Dashboard         │  │   │
│  │  └──────────────┘  └───────────────┘  └──────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  API / MIDDLEWARE COMPONENTS                                         │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │   │
│  │  │ REST API     │  │ Auth Module   │  │ Session Manager          │  │   │
│  │  └──────────────┘  └───────────────┘  └──────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  BUSINESS LOGIC COMPONENTS                                           │   │
│  │  ┌──────────────────────────────────────────────────┐                │   │
│  │  │ Forensic Analysis Subsystem                      │                │   │
│  │  │  ┌────────────────┐  ┌────────────┐              │                │   │
│  │  │  │MetadataAnalyzer│  │ELAProcessor│              │                │   │
│  │  │  └────────────────┘  └────────────┘              │                │   │
│  │  │  ┌──────────────────────────────────┐            │                │   │
│  │  │  │      ForensicEngine (Orchestrator)│            │                │   │
│  │  │  └──────────────────────────────────┘            │                │   │
│  │  └──────────────────────────────────────────────────┘                │   │
│  │  ┌──────────────────────────────────────────────────┐                │   │
│  │  │ Decision Engine Subsystem                        │                │   │
│  │  │  ┌────────────────┐  ┌──────────────────┐       │                │   │
│  │  │  │AISemanticChecker│ │TrustScoreCalculator│      │                │   │
│  │  │  └────────────────┘  └──────────────────┘       │                │   │
│  │  │  ┌──────────────┐    ┌──────────────────┐       │                │   │
│  │  │  │DecisionRouter│    │  ScoreWeights     │       │                │   │
│  │  │  └──────────────┘    └──────────────────┘       │                │   │
│  │  └──────────────────────────────────────────────────┘                │   │
│  │  ┌──────────────────────────────────────────────────┐                │   │
│  │  │ Domain Entities                                  │                │   │
│  │  │  ┌──────────────┐  ┌────────┐  ┌──────────────┐ │                │   │
│  │  │  │RefundDispute │  │Evidence│  │  FraudAlert   │ │                │   │
│  │  │  └──────────────┘  └────────┘  └──────────────┘ │                │   │
│  │  └──────────────────────────────────────────────────┘                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  DATA & EXTERNAL SERVICE COMPONENTS                                  │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │   │
│  │  │ User DB      │  │ Transaction   │  │ Evidence Archive         │  │   │
│  │  │ (Supabase)   │  │ Logs (PgSQL)  │  │ (Hashed Image Store)    │  │   │
│  │  └──────────────┘  └───────────────┘  └──────────────────────────┘  │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐  │   │
│  │  │ Vector DB    │  │ Refund API    │  │ Notification Service     │  │   │
│  │  │ (Pinecone)   │  │ (Banking)     │  │ (Email/SMS/Push)        │  │   │
│  │  └──────────────┘  └───────────────┘  └──────────────────────────┘  │   │
│  │  ┌──────────────┐                                                    │   │
│  │  │ Gemini 1.5   │                                                    │   │
│  │  │ AI Model API │                                                    │   │
│  │  └──────────────┘                                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component List

### 1. Frontend Components (Presentation Layer)

| # | Component | Description |
|---|-----------|-------------|
| 1 | **Chat Interface** | Streamlit/React-based conversational UI that collects dispute context from the customer, displays dispute status, refund confirmations, and notifications. Implements FR 1.1. |
| 2 | **Live Camera Capture Module** | HTML5 Media Capture API widget that enforces real-time image capture, programmatically disabling gallery uploads to prevent submission of pre-edited images. Implements FR 1.2. |
| 3 | **Admin Dashboard** | Web interface for system administrators to view fraud analytics, configure trust score thresholds/weights, and generate system reports. Linked to `SystemAdmin` class. |
| 4 | **Support Agent Panel** | Interface for support agents to review fraud alerts, view evidence packages (original image + ELA overlay + metadata report), and make manual review decisions. Linked to `SupportAgent` class. |

---

### 2. API / Middleware Components (Application Layer)

| # | Component | Description |
|---|-----------|-------------|
| 5 | **FastAPI REST API** | Backend API server exposing RESTful endpoints: `/api/dispute/submit`, `/api/dispute/status/{id}`, `/api/admin/analytics`, `/api/admin/config`. Handles request parsing, validation, and routing to business logic. |
| 6 | **Authentication Module** | Validates user credentials (login/logout), generates and verifies JWT session tokens. Maps to `User.login()` and `User.validateCredentials()` from the UML class diagram. |
| 7 | **Session & Rate Limiter** | Manages active user sessions and enforces rate limits to prevent abuse. Supports NFR 2 (scalability under concurrent requests). |
| 8 | **Evidence Hashing Service** | Computes SHA-256 hash of submitted evidence images at the API boundary for integrity verification. Maps to Process 2.0 (Evidence Collection & Hashing) from the Level 1 DFD. |

---

### 3. Business Logic Components — Forensic Analysis Subsystem

| # | Component | Description |
|---|-----------|-------------|
| 9 | **MetadataAnalyzer** | Parses EXIF data from submitted images, extracts device make/model/software fields, and detects suspicious software signatures (Adobe, GIMP, Stable Diffusion, etc.). Returns a binary metadata score (0 or 1). Implements FR 2.1. |
| 10 | **ELAProcessor** | Performs Error Level Analysis: re-saves the image at known JPEG quality (90%), calculates pixel differences, amplifies them (×50), and computes a variance score. Authentic images show uniform noise; manipulated regions glow bright. Implements FR 2.2. |
| 11 | **ForensicEngine** | Orchestrator that combines `MetadataAnalyzer` and `ELAProcessor` via aggregation. Invokes both analyses, aggregates flags (e.g., `SUSPICIOUS_SOFTWARE_DETECTED`, `METADATA_STRIPPED`), and produces a unified `ForensicResult`. |

---

### 4. Business Logic Components — Decision Engine Subsystem

| # | Component | Description |
|---|-----------|-------------|
| 12 | **AISemanticChecker** | Sends evidence images + user claims to Google Gemini 1.5 Flash API for semantic consistency verification (e.g., verifying the described "burnt crust" matches the visual data). Returns a confidence score (0.0–1.0). Implements FR 3.1. |
| 13 | **TrustScoreCalculator** | Computes the final Trust Score using the weighted ensemble formula: `T = w₁(S_meta) + w₂(S_ela) + w₃(S_ai)`. Default weights: metadata=0.20, ELA=0.35, AI=0.45. Implements FR 4.1. |
| 14 | **ScoreWeights** | Configuration data class holding the three ensemble weights. Includes validation to ensure weights are non-negative and sum to 1.0. Supports admin-configurable thresholds. |
| 15 | **DecisionRouter** | Routes disputes based on trust score thresholds: `T > 0.9` → Auto-Refund API (FR 4.2), `T < 0.5` → Fraud Alert to agent (FR 4.3), `0.5 ≤ T ≤ 0.9` → Manual Review queue. |
| 16 | **FraudAlert** | Domain entity representing a fraud alert created for a support agent, containing dispute ID, trust score, flags, priority level, and timestamp. |

---

### 5. Domain Entity Components

| # | Component | Description |
|---|-----------|-------------|
| 17 | **User** (Abstract) | Base class with common attributes (userId, email, passwordHash) and methods (login, logout, updateProfile). Extended by RegisteredUser, SupportAgent, SystemAdmin. |
| 18 | **RegisteredUser** | Customer entity with dispute history, trust level, and methods to initiate disputes and upload evidence. |
| 19 | **SupportAgent** | Human reviewer entity with assigned disputes, resolved count, and methods for reviewing fraud alerts and making manual decisions. |
| 20 | **SystemAdmin** | Administrator entity with permissions to update trust thresholds, view analytics, and configure system parameters. |
| 21 | **RefundDispute** | Core domain entity representing a refund dispute with status tracking, trust score, decision type, and assigned agent. Contains a composition relationship with Evidence (1 : 1..*). |
| 22 | **Evidence** | Image evidence entity storing the image data, SHA-256 hash, capture timestamp, capture mode (live/gallery), and individual forensic scores (metadata, ELA, AI). |

---

### 6. Data & External Service Components (Data Layer)

| # | Component | Description |
|---|-----------|-------------|
| 23 | **User Database** (Supabase/PostgreSQL) | Stores user profiles, hashed credentials, and session data. Corresponds to data store D1 in the Level 1 DFD. |
| 24 | **Transaction Logs** (PostgreSQL) | Records all dispute transactions, trust scores, decisions, and routing outcomes. Corresponds to data store D2. |
| 25 | **Evidence Archive** | Secure storage for hashed evidence images and associated forensic metadata. Images processed ephemerally (NFR 3) and archived only for confirmed fraud. Corresponds to data store D3. |
| 26 | **Fraud Analytics Store** | Stores confirmed fraud cases, patterns, and historical analytics for admin dashboard consumption. Corresponds to data store D4. |
| 27 | **Configuration Store** | Persists system configuration: trust score weights, decision thresholds, API keys, and feature flags. Corresponds to data store D5. |
| 28 | **Pinecone Vector DB** | Vector database for duplicate image detection — generates embeddings of submitted images and performs similarity searches to catch re-used fraudulent evidence. |
| 29 | **Refund API** (External - Banking) | External banking gateway interface for processing automated refunds. Called by `DecisionRouter` when `T > 0.9`. Methods: `initiateRefund()`, `checkRefundStatus()`, `cancelRefund()`. |
| 30 | **Notification Service** (External) | Multi-channel notification delivery system (email, SMS, push notifications) for informing customers about dispute status, refund confirmations, and fraud alerts. |
| 31 | **Gemini 1.5 Flash API** (External - Google) | External Vision-Language Model API that receives image + context payloads and returns semantic consistency confidence scores. Used by `AISemanticChecker`. |

---

### Component Summary

| Category | Count | Examples |
|----------|-------|---------|
| Frontend Components | 4 | Chat Interface, Live Camera, Admin Dashboard, Agent Panel |
| API / Middleware Components | 4 | FastAPI, Auth Module, Session Manager, Hashing Service |
| Forensic Analysis Components | 3 | MetadataAnalyzer, ELAProcessor, ForensicEngine |
| Decision Engine Components | 5 | AISemanticChecker, TrustScoreCalculator, ScoreWeights, DecisionRouter, FraudAlert |
| Domain Entity Components | 6 | User (abstract), RegisteredUser, SupportAgent, SystemAdmin, RefundDispute, Evidence |
| Data & External Services | 9 | User DB, Transaction Logs, Evidence Archive, Fraud Analytics, Config Store, Pinecone, Refund API, Notification Service, Gemini API |
| **Total** | **31** | |

---
