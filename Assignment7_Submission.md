# Assignment 7 Submission
## CS 331 Software Engineering Lab
## VeriSupport: Autonomous Multimodal Customer Support & Forensic Integrity System

---

# Q1. Business Logic Layer — Core Functional Modules & UI Integration 

## BLL Architecture Overview

The Business Logic Layer (BLL) acts as a mediator between the **Presentation Layer** (Assignment 6: Flask Web App, Streamlit Portals, Admin CLI) and the **Service/Data Layer** (Assignments 3-5: ForensicEngine, TrustScoreCalculator, DecisionRouter).

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│  Flask Web App (app_with_bll.py)  │  Streamlit  │  CLI         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              BUSINESS LOGIC LAYER (Assignment 7)                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         DisputeManagementBLL (Orchestrator)             │   │
│  │  • Input validation    • Lifecycle management           │   │
│  │  • Duplicate prevention • Status transitions            │   │
│  │  • Pipeline coordination                                │   │
│  └───────┬──────────┬─────────────┬──────────────┬────────┘   │
│          │          │             │              │              │
│  ┌───────▼──────┐ ┌─▼───────────┐ ┌▼────────────┐ ┌▼─────────┐│
│  │ ForensicBLL  │ │ DecisionBLL │ │ UserMgmtBLL│ │NotifBLL  ││
│  │ • Validate   │ │ • Validate  │ │ • Auth     │ │• Template││
│  │ • Analyze    │ │ • TrustScore│ │ • RBAC     │ │• Channel ││
│  │ • Transform  │ │ • Route     │ │ • Session  │ │• Deliver ││
│  └──────────────┘ └─────────────┘ └────────────┘ └──────────┘│
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               SERVICE LAYER (Assignment 5)                      │
│  ForensicAnalysisService  │  DecisionEngineService              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               DATA LAYER (Assignments 3-4)                      │
│  ForensicEngine  │  TrustScoreCalculator  │  DecisionRouter     │
└─────────────────────────────────────────────────────────────────┘
```

---

## BLL Modules Implemented

### Module 1: `bll_dispute_management.py` — Dispute Management BLL (Orchestrator)

**Role**: Central orchestrator that coordinates the full dispute lifecycle by invoking all other BLL modules in sequence.

**Key Class**: `DisputeManagementBLL`

**Responsibilities**:
- Validates all dispute inputs (order ID, amount, description, image)
- Prevents duplicate dispute submissions (same order within 24 hours)
- Orchestrates the pipeline: **Validation → Forensic Analysis → Decision Engine → Notifications**
- Manages dispute status transitions with enforcement (e.g., cannot go from `APPROVED` to `REJECTED`)
- Transforms combined results into a unified `DisputeSummary` DTO for the UI

**Integration with Presentation Layer**:
```python
# In app_with_bll.py (Flask route)
@app.route('/api/dispute/submit', methods=['POST'])
def api_submit_dispute():
    # Extract form data from UI
    order_id = request.form.get('order_id')
    amount = float(request.form.get('amount'))
    image_data = request.files.get('image').read()
    
    # ALL processing goes through the BLL
    summary = dispute_bll.submit_dispute(
        order_id=order_id,
        amount=amount,
        description=request.form.get('description'),
        image_data=image_data,
    )
    
    # BLL returns DisputeSummary DTO — already transformed for UI
    return jsonify(dispute_bll.to_dict(summary))
```

---

### Module 2: `bll_forensic_analysis.py` — Forensic Analysis BLL

**Role**: Wraps the Forensic Analysis Service (Assignment 5) with input validation, business-rule-based flagging, and data transformation.

**Key Class**: `ForensicAnalysisBLL`

**Responsibilities**:
- Validates image inputs (format via magic bytes, size ≤ 10MB, allowed types)
- Detects duplicate image submissions via SHA-256 hash with cooldown period
- Delegates actual forensic analysis to `ForensicAnalysisService`
- Applies business rules for additional flagging (e.g., multiple manipulation indicators)
- Transforms raw forensic scores into a `RiskAssessment` DTO with risk levels, colors, and human-readable labels

**Integration with Presentation Layer**:
The `ForensicAnalysisBLL` is invoked by `DisputeManagementBLL` during dispute submission. The UI receives the transformed `RiskAssessment` fields as part of the `DisputeSummary`:
```
Raw metadata_score: 0.0  →  "Suspicious — Editing software detected"
Raw ela_score: 0.72      →  "Minor — Slight compression inconsistencies"
Raw overall: 0.36        →  Risk Level: "high", Color: "#e67e22"
```

---

### Module 3: `bll_decision_engine.py` — Decision Engine BLL

**Role**: Wraps the Decision Engine Service (Assignment 5) with business-rule overrides, validation, and transformation into actionable decision reports.

**Key Class**: `DecisionEngineBLL`

**Responsibilities**:
- Validates all input scores [0, 1] and order amounts [$1 - $10,000]
- Applies business rule overrides:
  - **High-value orders** (>$500): Auto-refund overridden to manual review
  - **Repeat fraud users** (≥3 alerts): Automatically escalated to fraud alert
  - **Low confidence + auto-refund**: Downgraded to manual review
- Transforms raw results into `DecisionReport` DTO with formatted labels, color codes, formula display, and actionable recommendations

**Integration with Presentation Layer**:
```
Raw trust_score: 0.6370        →  Display: "63%", Color: "#f39c12"
Raw decision: "manual_review"  →  "🔍 QUEUED FOR MANUAL REVIEW"
Raw action: "queued_for_..."   →  "A support agent will review within 24 hours"
```

---

### Module 4: `bll_user_management.py` — User Management BLL

**Role**: Implements user authentication, session management, and role-based access control (RBAC).

**Key Class**: `UserManagementBLL`

**Responsibilities**:
- Validates email format and password strength (≥8 chars, uppercase, digit)
- Enforces login rate limiting (max 5 attempts per 15 minutes)
- Creates sessions with role-specific permissions
- Provides authorization checks against a permissions matrix

**Roles & Permissions**:

| Role | Key Permissions |
|------|----------------|
| Customer | `dispute:submit`, `dispute:view_own`, `evidence:upload` |
| Agent | `dispute:view_all`, `dispute:review`, `dispute:approve`, `dispute:reject` |
| Admin | All permissions including `config:edit`, `system:manage_services`, `user:manage` |

**Integration with Presentation Layer**:
```python
# Login route → BLL handles validation, rate limiting, session creation
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    response = user_bll.login(email, password)
    # BLL transforms UserRecord → SessionContext with permissions
    return jsonify({'session': response.session})
```

---

### Module 5: `bll_notification.py` — Notification BLL

**Role**: Orchestrates multi-channel notification delivery using templates, with channel selection based on business priority rules.

**Key Class**: `NotificationBLL`

**Responsibilities**:
- Validates recipient addresses (email format, phone format)
- Selects notification channels based on decision priority:
  - **Normal** (auto-refund, manual review): Email + Push
  - **High** (fraud alert): Email + SMS + Push
- Generates messages from templates using decision context
- Enforces rate limiting (max 10 notifications per user per hour)

**Integration with Presentation Layer**:
The notification BLL is invoked automatically at the end of the dispute pipeline. The UI receives notification counts and channels used.

---

## Presentation Layer Integration — Flask App (`app_with_bll.py`)

The Flask web application (`app_with_bll.py`) demonstrates the clear separation between layers:

| Flask Route | BLL Module Called | Purpose |
|-------------|------------------|---------|
| `POST /api/dispute/submit` | `DisputeManagementBLL.submit_dispute()` | Submit new dispute |
| `GET /api/disputes` | `DisputeManagementBLL.list_disputes()` | List disputes for agent |
| `POST /api/dispute/<id>/approve` | `DisputeManagementBLL.update_dispute_status()` | Approve dispute |
| `POST /api/auth/login` | `UserManagementBLL.login()` | User login |
| `GET /api/stats` | `DisputeManagementBLL.get_stats()` | System statistics |

The routes **never** directly call the service layer. All business logic, validation, and data transformation happen within the BLL before responses reach the UI.

---

## Running the Demo

```bash
cd "Assignment 7"
python demo_bll.py       # Full BLL demo with all modules
python app_with_bll.py   # Flask web app with BLL integration
```

---

# Q2A. Business Rules Implementation 

Business rules are the rules and conditions the application follows to perform various operations. Below are the business rules implemented in each BLL module.

## Forensic Analysis Module — Business Rules

| Rule # | Rule Description | Implementation | File/Function |
|--------|-----------------|----------------|---------------|
| FA-1 | Maximum image size is 10 MB | `if len(image_data) > MAX_IMAGE_SIZE_BYTES: raise ValidationError` | `bll_forensic_analysis.py` / `validate_image()` |
| FA-2 | Only JPEG and PNG formats are accepted | Magic byte detection: `\xff\xd8\xff` = JPEG, `\x89PNG` = PNG | `bll_forensic_analysis.py` / `_detect_image_format()` |
| FA-3 | Duplicate images have a 60-second cooldown | SHA-256 hash tracked with timestamp; resubmissions within window flagged | `bll_forensic_analysis.py` / `check_duplicate()` |
| FA-4 | Multiple manipulation indicators trigger combined flag | If both `metadata_score < 0.3` and `ela_score < 0.4`, add `MULTIPLE_MANIPULATION_INDICATORS` flag | `bll_forensic_analysis.py` / `_apply_business_rules()` |
| FA-5 | Risk level classification | Score ranges: ≥0.85 = Very Low, ≥0.70 = Low, ≥0.50 = Medium, ≥0.30 = High, <0.30 = Critical | `bll_forensic_analysis.py` / `_score_to_risk_level()` |

## Decision Engine Module — Business Rules

| Rule # | Rule Description | Implementation | File/Function |
|--------|-----------------|----------------|---------------|
| DE-1 | Trust Score Formula: `T = 0.20×S_meta + 0.35×S_ela + 0.45×S_ai` | Weighted ensemble calculation with configurable weights | `trust_score_calculator.py` / `calculate_trust_score()` |
| DE-2 | Auto-refund threshold: `T > 0.9` | If trust score exceeds 0.9, dispute is auto-approved for refund | `trust_score_calculator.py` / `get_recommended_action()` |
| DE-3 | Fraud alert threshold: `T < 0.5` | If trust score is below 0.5, fraud alert is created | `trust_score_calculator.py` / `get_recommended_action()` |
| DE-4 | Manual review: `0.5 ≤ T ≤ 0.9` | Scores in middle range are queued for human agent review | `trust_score_calculator.py` / `get_recommended_action()` |
| DE-5 | High-value order override: Amount > $500 → always manual review | Overrides auto-refund to manual review for expensive orders | `bll_decision_engine.py` / `_apply_business_rules()` |
| DE-6 | Repeat fraud escalation: ≥3 alerts → auto-reject | Users with 3+ previous fraud alerts are automatically escalated | `bll_decision_engine.py` / `_apply_business_rules()` |
| DE-7 | Low confidence downgrade | Auto-refund with low confidence is downgraded to manual review | `bll_decision_engine.py` / `_apply_business_rules()` |

## Dispute Management Module — Business Rules

| Rule # | Rule Description | Implementation | File/Function |
|--------|-----------------|----------------|---------------|
| DM-1 | Order amount limits: $1 - $10,000 | Validated before processing | `bll_dispute_management.py` / `validate_amount()` |
| DM-2 | Duplicate prevention within 24 hours | Same order ID cannot be disputed twice within 24 hours | `bll_dispute_management.py` / `check_duplicate_dispute()` |
| DM-3 | Status transition enforcement | Only valid transitions allowed (e.g., PENDING→UNDER_REVIEW, not APPROVED→REJECTED) | `bll_dispute_management.py` / `update_dispute_status()` |
| DM-4 | Description length: 10-1000 characters | Too short or too long descriptions are rejected | `bll_dispute_management.py` / `validate_description()` |

## User Management Module — Business Rules

| Rule # | Rule Description | Implementation | File/Function |
|--------|-----------------|----------------|---------------|
| UM-1 | Login rate limiting: max 5 attempts per 15 minutes | Failed attempts tracked per email with sliding window | `bll_user_management.py` / `_is_locked_out()` |
| UM-2 | Role-based access control (RBAC) | Three roles (customer, agent, admin) with specific permission sets | `bll_user_management.py` / `PERMISSIONS` dict |
| UM-3 | Session expiry: 8 hours | Sessions automatically invalidated after 8 hours | `bll_user_management.py` / `authorize()` |

## Notification Module — Business Rules

| Rule # | Rule Description | Implementation | File/Function |
|--------|-----------------|----------------|---------------|
| NF-1 | Channel selection by priority | Normal→Email+Push; High→Email+SMS+Push; Urgent→All channels | `bll_notification.py` / `CHANNEL_RULES` |
| NF-2 | Rate limiting: max 10 per user per hour | Prevents notification spam | `bll_notification.py` / `_is_rate_limited()` |
| NF-3 | Template-based messages | Different templates for auto-refund, manual review, fraud alert | `bll_notification.py` / `NOTIFICATION_TEMPLATES` |

---

# Q2B. Validation Logic 

Validation logic ensures that all inputs conform to expected formats, ranges, and business constraints before processing.

## Types of Validation

### 1. Input Format Validation

These checks ensure data is in the correct format:

| Module | Field | Validation Rule | Error Example |
|--------|-------|-----------------|---------------|
| Forensic BLL | Image format | Magic byte detection (JPEG: `\xff\xd8\xff`, PNG: `\x89PNG`) | "Unsupported image format. Allowed: JPEG, PNG" |
| Forensic BLL | Image size | `len(data) ≤ 10 MB` | "Image size (12.5 MB) exceeds maximum (10 MB)" |
| Decision BLL | Score values | `0.0 ≤ score ≤ 1.0` for all three scores | "Must be between 0.0 and 1.0, got 1.5" |
| User BLL | Email | Regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` | "Invalid email format: not-an-email" |
| User BLL | Password | Min 8 chars + 1 uppercase + 1 digit | "Password must contain at least one uppercase letter" |
| Dispute BLL | Order ID | Only alphanumeric, hyphens, underscores; min 3 chars | "Order ID must contain only letters, numbers, hyphens" |
| Notification BLL | Phone | Min 10 digits after removing formatting | "Invalid phone number" |

### 2. Business Constraint Validation

These checks enforce business rules:

| Module | Constraint | Validation Rule | Error Example |
|--------|-----------|-----------------|---------------|
| Dispute BLL | Order amount | `$1.00 ≤ amount ≤ $10,000.00` | "Minimum order amount is $1.00" |
| Dispute BLL | Description | `10 ≤ length ≤ 1000` characters | "Description must be at least 10 characters" |
| Dispute BLL | Duplicate prevention | Same order ID blocked within 24 hours | "A dispute for order 'ORD-001' was already submitted" |
| Dispute BLL | Status transition | Only valid transitions (defined in `VALID_TRANSITIONS` matrix) | "Cannot transition from 'approved' to 'rejected'" |
| Decision BLL | Weight sum | `w1 + w2 + w3 = 1.0` and all `≥ 0` | "Weights must sum to 1.0" |

### 3. Implementation Pattern — `ValidationError`

All BLL modules use a consistent `ValidationError` exception pattern:

```python
class ValidationError(Exception):
    """Raised when input validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field      # Which field failed
        self.message = message  # Human-readable error message

# Usage in Flask routes:
try:
    summary = dispute_bll.submit_dispute(...)
    return jsonify(dispute_bll.to_dict(summary))
except ValidationError as e:
    return jsonify({'error': e.message, 'field': e.field}), 400
```

This pattern ensures:
- **Consistent error handling** across all modules
- **Field-level feedback** for UI error highlighting
- **User-friendly messages** that can be displayed directly in the UI

---

# Q2C. Data Transformation 

Data transformation converts raw service-layer data and database records into UI-ready formats for the presentation layer.

## Transformation Overview

```
RAW DATA (Service/Data Layer)         UI-READY DATA (BLL Output)
────────────────────────────    →     ────────────────────────────
metadata_score: 0.0                   "Suspicious — Editing 
                                       software detected"
ela_score: 0.72                       "Minor — Slight 
                                       compression inconsistencies"
overall: 0.36                         Risk Level: "high"
                                      Color: "#e67e22"
trust_score: 0.6370                   "63%", gauge color: orange
decision: "manual_review"            "QUEUED FOR MANUAL REVIEW"
action: "queued_for_review"          "A support agent will review 
                                      within 24 hours"
flags: ["META_STRIPPED"]              "Image metadata has been 
                                       removed"
User record (DB row)                  SessionContext with role 
                                       label + permissions list
Decision event                        Templated email/SMS/push 
                                       notification payloads
```

## Transformation Details by Module

### 1. Forensic Analysis BLL — `RiskAssessment` DTO

**Transforms**: Raw forensic scores (floats) → labeled risk assessment

| Raw Field | Transformation | UI-Ready Output |
|-----------|---------------|-----------------|
| `metadata_score` (0.0-1.0) | `_metadata_score_to_label()` | `"Clean"` / `"Partial"` / `"
Suspicious"` |
| `ela_score` (0.0-1.0) | `_ela_score_to_label()` | `"Authentic"` / `"Minor"` / `"Moderate"` / `"Severe"` |
| `(meta + ela) / 2` | `_score_to_risk_level()` | Risk level (very_low/low/medium/high/critical) with CSS color |
| Flag codes (e.g., `SUSPICIOUS_SOFTWARE_DETECTED`) | `FLAG_DESCRIPTIONS` lookup | Human-readable explanation strings |

```python
# Example transformation
@dataclass
class RiskAssessment:
    risk_level: str       # "high"
    risk_label: str       # "High Risk — Significant manipulation indicators"
    risk_color: str       # "#e67e22"
    metadata_label: str   # "Suspicious — Editing software detected"
    ela_label: str        # "Minor — Slight compression inconsistencies"
    flag_descriptions: List[str]  # ["Image metadata has been removed"]
```

### 2. Decision Engine BLL — `DecisionReport` DTO

**Transforms**: Raw trust score + decision → actionable report

| Raw Field | Transformation | UI-Ready Output |
|-----------|---------------|-----------------|
| `trust_score` (float) | Formatted + percentage | `"0.6370"`, `63`, `"#f39c12"` |
| `decision` (code) | `DECISION_DISPLAY` lookup | Label + icon + color |
| Component scores | `_score_to_component_label()` | `" Metadata: 1.00 — Passed"` |
| Score calculation | Formula builder | `"T = 0.20×1.00 + 0.35×0.72 + 0.45×0.85 = 0.6345"` |
| Decision type | `_generate_recommendations()` | List of actionable next steps |

```python
# Example transformation
@dataclass
class DecisionReport:
    trust_score_display: str    # "0.6370"
    trust_score_percentage: int # 63
    decision_label: str         # "QUEUED FOR MANUAL REVIEW"
    decision_icon: str          # ""
    decision_color: str         #" #f39c12"
    formula_display: str        # "T = 0.20×1.00 + 0.35×0.72 + 0.45×0.85 = 0.6345"
    recommendations: List[str]  # ["Agent will review within 24 hours", ...]
```

### 3. User Management BLL — `SessionContext` DTO

**Transforms**: Raw database user record → authenticated session context

| Raw Field | Transformation | UI-Ready Output |
|-----------|---------------|-----------------|
| `role` (string) | `ROLE_LABELS` lookup | `"🛒 Customer"` / `"🎧 Support Agent"` / `"⚙️ Administrator"` |
| `role` | `PERMISSIONS` matrix lookup | List of permission strings |
| User record | Session creation | Session ID, expiry time, login time |

### 4. Notification BLL — `NotificationPayload` DTOs

**Transforms**: Decision events → formatted multi-channel messages

| Raw Input | Transformation | UI-Ready Output |
|-----------|---------------|-----------------|
| `decision: "auto_refund"` | Template selection + context fill | "Your Refund Has Been Approved — VeriSupport" |
| `amount: 49.99` | Template interpolation | "Your refund of $49.99 has been approved!" |
| `decision: "fraud_alert"` | Priority mapping → channel selection | Email + SMS + Push (high priority = all channels) |

### 5. Dispute Management BLL — `DisputeSummary` DTO (Combined)

**Transforms**: Results from ALL modules into a single unified response

The `DisputeSummary` is the **master DTO** that combines:
- Forensic risk assessment fields
- Decision report fields
- Notification delivery summary
- Dispute metadata (status, timeline, timestamps)

This ensures the presentation layer receives **one complete object** instead of managing multiple service responses.

```python
# The UI makes one call and gets everything:
summary = dispute_bll.submit_dispute(order_id, amount, description, image)

# All transformed data is included:
summary.status_label       # "Under Review"
summary.risk_label         # "High Risk"
summary.decision_label     # "QUEUED FOR MANUAL REVIEW"
summary.formula_display    # "T = 0.20×0.00 + 0.35×0.72 + 0.45×0.85 = 0.6345"
summary.notifications_sent # 2
summary.recommendations    # ["Agent will review within 24 hours", ...]
summary.timeline           # [{"step": "Validation", "status": "completed"}, ...]
```

---

## Files Implemented

| File | Type | Description |
|------|------|-------------|
| `bll_forensic_analysis.py` | BLL Module | Image validation, forensic analysis orchestration, risk assessment |
| `bll_decision_engine.py` | BLL Module | Trust score validation, business rule overrides, decision reports |
| `bll_user_management.py` | BLL Module | Authentication, RBAC, session management |
| `bll_notification.py` | BLL Module | Template-based multi-channel notification delivery |
| `bll_dispute_management.py` | BLL Module (Orchestrator) | Full dispute lifecycle management, combines all modules |
| `app_with_bll.py` | Integration | Flask web app using BLL instead of direct service calls |
| `demo_bll.py` | Demo | Runnable demonstration of all BLL modules |

---

*End of Assignment 7 Submission*
