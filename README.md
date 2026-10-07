---
title: Lokr Sentinel 2.0
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.31.0
app_file: app.py
pinned: false
---

<div align="center">

# 🛡️ Lokr Assistant — Sentinel 2.0

### Multi-Agent Codebase Defense & Orchestration

**Diagnose bugs. Review diffs. Gate deployments. All grounded in your actual codebase.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-000000.svg)](https://ollama.com)
[![Agent Autonomy](https://img.shields.io/badge/Agents-Autonomous-brightgreen.svg)]()
[![Context Efficient](https://img.shields.io/badge/Context-Minimal%20Injection-blue.svg)]()
[![Fail-Loud](https://img.shields.io/badge/Validation-Fail--Loud-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

### Features at a Glance

- **3 Modes** — Repair, Review, and Prevent
- **Agent Autonomy** — Agents call Lokr on their own via `lokr_requests`, not orchestrator-driven
- **Minimal Context Injection** — Analyzer starts with only a bug report and entry points, then requests more context as needed
- **Fast-Path Revisions** — Safety → Action targeted feedback avoids restarting the full pipeline
- **Fail-Loud Validation** — Token tracking, grounding ratio logging, explicit errors on malformed output

### ⚠️ Configuration Note
To run this multi-agent system, configure the LLM backend via the UI sidebar:
1. **API URL & Key:** Input your own OpenAI-compatible API URL and API Key. Examples are provided in the UI placeholders.
2. **Model Selection:** Input the exact Model Name for your chosen provider.
3. **Minimum Requirements:** Use a model with **33B parameters or higher** (e.g., `Qwen2.5-Coder-32B-Instruct`). The framework orchestrates multiple agents that rely on complex JSON output parsing; smaller models will struggle with context truncation.

</div>

---

## 🎯 What Is Lokr Assistant?

**Lokr** is the code search engine — it parses source files with Tree-sitter, builds a call graph with NetworkX, and stores embeddings in ChromaDB so queries return only the code that's relevant.

**Lokr Assistant (Sentinel 2.0)** is the multi-agent layer built on top — it uses Lokr's context to diagnose bugs, propose patches, review them for risks, and score deployment safety.

Together, the system acts as an AI engineering copilot. Unlike generic LLM coding tools that suffer from context bloat and hallucination, Lokr Assistant grounds its decision-making in a localized dependency graph using the Lokr engine.

### Design Choices

1. **Agentic Context Discovery** — Analyzer starts with only a bug report and entry points, then autonomously queries Lokr for the specific dependencies it needs instead of receiving everything upfront.

2. **Safety → Action Fast-Path** — Rejected patches don't trigger full pipeline restart. Safety agent provides targeted revision suggestions directly to Action, avoiding redundant work.

3. **Deterministic Pre-Scan** — Regex-based scanner catches common backdoor patterns (debug headers, hardcoded admin bypasses) before the LLM runs.

4. **Fail-Loud Architecture** — All agents validate their own JSON output, raising explicit errors if schemas are invalid rather than falling back to placeholder data.

---

## How It Compares

### vs. Generic AI Assistants (ChatGPT, Copilot, Claude)
- Findings are cross-referenced against Lokr's dependency graph instead of relying on the LLM's memory alone.
- Agents request code context on their own via `lokr_requests` instead of receiving a large pre-fetched dump.
- Malformed LLM outputs raise explicit errors instead of silently falling back to stub data.
- Safety rejections route directly to Action with `revision_suggestions` instead of restarting the full pipeline.
- A regex pre-scan catches known backdoor patterns (debug headers, auth bypasses) before the LLM runs.

### vs. Static Analysis Tools (Bandit, ESLint, SonarQube)
- Understands *why* code matters, not just AST patterns.
- Distinguishes between "safe README update" and "removed auth middleware."
- Produces human-readable diagnoses, not raw linter warnings.
- Risk scoring is contextual — the same bug is more severe in payment code than in logging.

### vs. Manual Code Review
- Runs on every request without context-switching overhead.
- Every decision is logged with timestamps for audit.
- Applies the same checks regardless of time of day.
- Deployment gate blocks unsafe changes automatically.

---

## 📊 Performance & Efficiency

### Context Optimization (Sentinel 2.0)

Lokr Assistant uses **agentic context discovery** instead of dumping all retrieved code upfront:

- The Analyzer starts with only the bug report and a few entry-point function names
- It autonomously issues `lokr_requests` to pull in specific dependencies as needed
- The orchestrator logs token estimates at each step via `[FORENSIC]` tags, and warns if input exceeds an 8k token budget
- This keeps the LLM focused on relevant code instead of sifting through unrelated files

### Token Flow Visualization

```
┌─────────────────────────────────────────────────────────┐
│ BEFORE: Orchestrator Pre-Fetches Everything             │
├─────────────────────────────────────────────────────────┤
│ Orchestrator:                                           │
│  - Finds relevant files via Lokr                        │
│  - Dumps ALL file summaries                             │
│  - Includes full middleware source                      │
│  - Adds relationship graph                              │
│  → Analyzer receives a large unfocused context          │
│  → LLM struggles with irrelevant information            │
│  → Hallucinations increase with context size            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ AFTER: Agentic Context Discovery                        │
├─────────────────────────────────────────────────────────┤
│ Orchestrator → Analyzer:                                │
│  "Here's the bug report + 2-3 entry functions"          │
│                                                         │
│ Analyzer → Orchestrator:                                │
│  "I need: dependencies of deletePet, auth middleware"   │
│                                                         │
│ Orchestrator → Lokr → Analyzer:                         │
│  [Results of requested queries only]                    │
│                                                         │
│ Analyzer re-runs with focused context                   │
│  → Produces grounded diagnosis                          │
│  → Fewer hallucinations (less context noise)            │
└─────────────────────────────────────────────────────────┘
```

### Evidence Grounding & Verification

Findings are checked against retrieved source code before being reported:

- **Verbatim Snippet Matching**: Findings include a `quoted_code` field checked against real code in retrieved files.
- **Auto-Fetch Recovery**: If a finding references code from an unretrieved file, the pipeline fetches the source via Lokr and retries (capped at 2 retries).
- **Explicit Grounding Flags**: Findings that remain unverified after retries are kept in the report but marked explicitly as `"grounded": false`.
- **Structured Grounding Metrics**: Every run returns summary metrics:

```json
"grounding": {
  "analysis_ratio": 1.0,
  "analysis_grounded": true,
  "patch_grounded": true,
  "report": "1 findings raised, 1 grounded, 0 unverified"
}
```

---

## 🏗️ Architecture & Data Flow

### System Architecture

```
Lokr-assistant/
├── app.py                          # Streamlit UI with live agent progress
├── main.py                         # CLI entry point
├── assistant_mcp_server.py        # Model Context Protocol (MCP) server interface
│
├── agents/                         # Individual agent implementations
│   ├── analyzer.py                 # Diagnosis & readiness assessment
│   ├── action.py                   # Patch generation & blocker identification
│   ├── safety.py                   # Risk scoring & go/no-go decisions
│   └── validator.py                # Fix validation & deploy checklists
│
├── modes/
│   └── orchestrator.py             # Single entry point for intent classification, agent loop, pre-scan, and forensics
│
├── lokr/
│   ├── client.py                   # HTTP client for Lokr
│   └── service.py                  # Graph-RAG integration layer
│
└── shared/
    ├── prompts.py                  # Mode-specific system prompts
    ├── llm_client.py               # Ollama LLM client
    └── base_agent.py               # Base agent class
```

### Agent Pipeline Flow

The orchestrator (`modes/orchestrator.py`) is the single pipeline entry point for both the Streamlit app and the CLI. All requests follow a unified code path for intent classification and agent execution.

```
User Request
    ↓
┌─────────────────────────────────────────┐
│ Intent Classifier                       │
│ (Fast: keywords + LLM tiebreaker)       │
└────┬────────┬────────┬────────┬─────────┘
     │        │        │        │
     ↓        ↓        ↓        ↓
  REPAIR   REVIEW   PREVENT  EXPLAIN
    │        │        │        │
    └────────┼────────┼────────┘
             ↓
    ┌────────────────────────────────┐
    │ Deterministic Pre-Scan         │
    │ (Regex for CAT-0 backdoors)    │
    └────────────────┬───────────────┘
                     ↓
    ┌────────────────────────────────┐
    │ ANALYZER AGENT                 │
    │ Input: Bug report + entry pts  │
    │ Output: Diagnosis + evidence   │
    │         + lokr_requests        │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼──────────────────┐
    │ Lokr Graph-RAG Loop           │
    │ Execute lokr_requests         │
    │ Append context, re-analyze    │
    └────────────┬──────────────────┘
                 ↓
    ┌────────────────────────────────┐
    │ ACTION AGENT                   │
    │ Input: Diagnosis + history     │
    │ Output: Patch/Blockers +       │
    │         revision_suggestions   │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼──────────────────┐
    │ SAFETY AGENT                  │
    │ Input: Proposed fix           │
    │ Output: Risk score + decision  │
    └────────────┬──────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
    ✅ PASS           ❌ REJECT
        │                  │
        ↓              ┌────▼────────────┐
    ┌────────────┐    │ Fast Path:      │
    │ VALIDATOR  │    │ Route to Action │
    │ (optional) │    │ + suggestions   │
    └────────────┘    │ Cap: 3 loops    │
        │              │ Then: Escalate  │
        ↓              └────┬───────────┘
    📋 RESULT              │
                           ↓
                    Full Analyzer Restart
                      (fallback)
```

### Mode-Specific Routing

```
INPUT: "Users can delete other people's pets"
  ↓
CLASSIFIER detects: repair
  ↓
REPAIR MODE PIPELINE:
  ├─ Pre-Scan: Checks for auth issues
  ├─ Analyzer: Diagnoses ownership check missing
  ├─ Action: Generates patch with ownership validation
  ├─ Safety: Confirms patch is safe
  ├─ Validator: Creates test cases
  └─ Output: Patch + tests + deployment notes

INPUT: "Is this code diff safe?"
  ↓
CLASSIFIER detects: review
  ↓
REVIEW MODE PIPELINE:
  ├─ Pre-Scan: Checks for logic inversions (|| → &&)
  ├─ Analyzer: Understands what changed
  ├─ Action: Recommends improvements
  ├─ Safety: Assesses deployment risk
  └─ Output: Review report + approval decision

INPUT: "Can I deploy?"
  ↓
CLASSIFIER detects: prevent
  ↓
PREVENT MODE PIPELINE:
  ├─ Pre-Scan: Hard-checks for blockers
  ├─ Analyzer: Deployment readiness
  ├─ Action: Identifies pre-deploy requirements
  ├─ Safety: Go/No-Go decision
  └─ Output: Readiness report + blockers
```

---

## 🔬 Key Architectural Mechanics

### 1. Agentic Context Discovery

**Problem:** Most AI systems pre-fetch all available context, overwhelming the LLM with irrelevant code.

**Solution:** Analyzer starts with minimal context (bug report + entry points) and autonomously requests additional details:

```
Analyzer: "I see a bug in deletePet. I need to understand the ownership validation."
Orchestrator: [executes lokr_requests: ["get dependencies of deletePet"]]
Lokr: [returns dependency graph + validation functions]
Analyzer: [re-analyzes with new context, produces grounded diagnosis]
```

**Benefit:** Analyzer stays focused on relevant code, reducing hallucinations.

### 2. Safety → Action Fast-Path Revision

**Problem:** When Safety rejects a patch, the entire pipeline restarts (2x cost).

**Solution:** Safety provides `revision_suggestions`; Action revises directly.

```
BEFORE (2x cost):
Safety rejects → Analyzer re-analyzes → Action re-patches → Safety re-checks

AFTER (0.3x cost):
Safety rejects (with suggestions) → Action revises → Safety re-checks
```

**Guardrails:**
- Capped at 3 iterations (prevents infinite loops)
- Falls back to Analyzer if no suggestions provided
- Escapes to full restart if needed

### 3. Deterministic Pre-Scan & Same-Class Endpoint Sweeping

**Problem:** LLMs sometimes miss critical security issues or stop after finding a single buggy endpoint.

**Solution:** Combining regex-based pre-scanning for CAT-0 patterns with prompt-enforced **Same-Class Endpoint Sweeping**:
- **Deterministic Pre-Scan**: Scans for `X-Debug: true` headers, hardcoded role overrides, and removed middleware before the LLM runs.
- **Same-Class Sweep Rule**: When a vulnerability pattern (e.g. missing auth check) is identified in one handler, the Analyzer automatically sweeps every handler in the file (`GET`, `PUT`, `POST`, `DELETE`) for the same pattern and reports each as a distinct finding.

**Output:** Mandatory findings injected into Analyzer context:
```
[PRESCAN] 🔴 Detected 2 backdoor pattern(s) across 10 files.
  [PRESCAN-001] Header-Based Auth Bypass in src/middleware/auth.js:10
  [PRESCAN-002] Hardcoded Role Escalation in src/middleware/auth.js:11
```

### 4. Fail-Loud Schema Validation

**Problem:** LLMs sometimes return malformed JSON; systems silently degrade to stubs.

**Solution:** All agents validate their own output; invalid schemas raise `ValueError`.

```python
# BEFORE (silent failure):
if not parsed and response.strip():
    return {"diagnosis": "Code analysis (stub)...", "confidence": 0.5}  # Fake data!

# AFTER (explicit failure):
required_fields = {"chain_of_thought", "contribution", "lokr_requests"}
for field in required_fields:
    if field not in parsed:
        raise ValueError(f"Missing required field: {field}")
```

**Orchestrator catches and terminates:**
```
state["status"] = "failed"
state["error"] = "ANALYZER_VALIDATION_ERROR: Missing required field: contribution"
```

### 5. Evidence Grounding & Auto-Fetch Recovery

**Problem:** Standard LLMs can hallucinate code snippets or drop findings when full context isn't available.

**Solution:** Findings are verified against actual retrieved source:
- **Snippet Matching**: `is_finding_grounded` checks quoted snippets against retrieved file contents (empty quotes return `False`).
- **Auto-Fetch Recovery**: If grounding fails due to missing file context, Lokr pulls the file into state and retries analysis (capped at 2 retries).
- **Explicit Flags**: Findings that fail grounding are kept and tagged with `grounded: false` instead of disappearing silently.
- **Context Sync**: Auto-fetched source code is passed into the Action Agent's input so patches remain grounded.

---

## 🔑 Key Design Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Minimal Context Injection** | Analyzer starts with bug report + entry points instead of full code dump | Focused context, fewer hallucinations |
| **Deterministic Pre-Scan** | Regex catches CAT-0 patterns before LLM | Can't hallucinate away security issues |
| **Fail-Loud Agents** | Agents raise `ValueError` on malformed output | No silent degradation to stubs |
| **Safety → Action Fast-Path** | Targeted revisions skip Analyzer | Avoids redundant pipeline restarts |
| **Token-Based Evidence** | Meaningful code tokens instead of substrings | Handles LLM abbreviations correctly |
| **Cascading Skepticism** | Each agent distrusts unverified claims | Grounded findings only |
| **Cross-Referencing** | Action reads both Analyzer + raw input | Catches dropped evidence |
| **Automatic Blockers** | Security conditions hardcoded (LLM can't override) | Prevents rubber-stamping |
| **LLM + Fast-Path Classification** | Keywords + LLM tiebreaker | Instant intent detection |
| **Progress Callbacks** | Real-time `st.status` updates | Transparent pipeline |

---

## 🚀 Features

### 🔧 Repair Mode — *"Fix this bug"*
- Diagnoses bugs using **verified code context** from Lokr
- Proposes targeted patches with exact file paths and line numbers
- Safety agent evaluates risk before any fix is accepted
- **Safety → Action fast-path**: Rejected patches get targeted revision suggestions without full pipeline restart
- Automatic revision loop if validation fails

### 📝 Review Mode — *"Is this diff safe?"*
- Analyzes code diffs for logic regressions, security issues, and quality
- **Mental execution of boolean logic** — detects when `||` → `&&` weakens validation
- Produces structured observations, recommendations, and an approval decision
- Catches subtle issues like weakened error handling conditions

### 🛡️ Prevent Mode — *"Can I deploy?"*
- **Deployment readiness gate** with evidence-grounded analysis
- Automatic blocker detection for:
  - 🔒 Removed authentication middleware
  - 💾 Required DB fields without migrations
  - ⚠️ FIXME comments that warn against merging
  - 🧪 Failing CI tests related to changed files
- Cross-references user claims against Lokr's file summaries
- Issues `SAFE_TO_DEPLOY`, `PROCEED_WITH_CAUTION`, or `NO_GO_FIX_BLOCKERS`

---

## 🎬 Demo Scenarios

> **Note:** The repository includes a `lokr-demo-app` directory which acts as the vulnerable target application for these scenarios. Make sure `./lokr-demo-app` is selected as the Project Directory in the UI.

### Scenario 1: Safe Deployment ✅

**Input:**
> *"We updated the README and tweaked some CSS. Can I deploy this?"*

**Expected Result:** 
```
✅ SAFE_TO_DEPLOY
Readiness: 100% | Risk: LOW
No blockers detected
```

---

### Scenario 2: Dangerous Deployment 🚫

**Input:**
> *"Can I deploy? I changed auth.js, admin.js, and User.js. I removed the admin middleware from the user list route and added a FIXME comment. I also added a required phoneNumber field to the User model without a migration. CI is showing one failing test."*

**Expected Result:** 
```
🚫 NO_GO_FIX_BLOCKERS
Readiness: 35% | Risk: CRITICAL

Blockers:
  [1] Authentication middleware removed from /admin route
  [2] FIXME comment warns against merging
  [3] Required DB field without migration plan
  [4] Failing CI test: test/users.spec.js (L45)
```

---

### Scenario 3: Backdoor Detection 🔴

**Input:**
> *"There's a bug in our pet API — users can delete other users' pets."*

**Pre-scan detects:**
```
[PRESCAN] 🔴 Detected 2 backdoor pattern(s) across 10 files.
  [PRESCAN-001] Header-Based Auth Bypass in src/middleware/auth.js:10
  [PRESCAN-002] Hardcoded Role Escalation in src/middleware/auth.js:11
```

**Expected Result:** 
Analyzer is forced to include these CAT-0 findings in its diagnosis, ensuring the backdoor is addressed in the patch.

```
🐛 BUG DIAGNOSIS

Root Cause:
Missing ownership check allows users to delete pets they don't own.
Additionally: Debug header in auth middleware disables authentication.

Findings:
  [CRITICAL] Missing ownershipCheck before deletePet()
  [CRITICAL] Debug header 'X-Debug: true' in auth.js:12 (pre-scanned)
  
Patch: Add ownership validation + remove debug header
```

---

### Scenario 4: Logic Regression Review 🔍

**Input:** Paste the following diff into the chat box:
```diff
--- a/src/middleware/permission.js
+++ b/src/middleware/permission.js
@@ -10,7 +10,7 @@ function checkAccess(req, res, next) {
     const isAdmin = req.user.role === 'admin';
     const hasPermission = req.user.permissions.includes('write');
 
-    if (!isAdmin || !hasPermission) {
+    if (!isAdmin && !hasPermission) {
         return res.status(403).json({ error: "Access Denied" });
     }
```

**Expected Result:** 
```
⚠️ REQUEST_CHANGES
Risk: HIGH

Observation:
The validation condition was weakened from 
  `if (!isAdmin || !hasPermission)` 
to 
  `if (!isAdmin && !hasPermission)`

This means unauthorized users can now pass if they're not an admin 
(regardless of permission check).

Recommendation:
Revert the operator change, or add explicit role checks.
```

---

## 🧠 How It Works: End-to-End

### Evidence Grounding Pipeline

```
User Input
    ↓
Intent Classifier (keywords + LLM)
    ↓
┌─────────────────────────────────────┐
│ Deterministic Pre-Scan              │
│ (Regex for CAT-0 backdoors)         │
│ Output: Mandatory safety findings   │
└──────────┬──────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ ANALYZER AGENT                      │
│ Input: Bug report + entry points    │
│        + pre-scan findings          │
│                                     │
│ Generates: diagnosis + evidence +   │
│            lokr_requests            │
└──────────┬──────────────────────────┘
           ↓
   ┌───────────────────┐
   │ lokr_requests     │ (autonomous)
   │ found?            │
   └────┬──────┬──────┘
        │      │
        ↓      ↓ No
       YES    Continue
        │
        ↓
   ┌────────────────────┐
   │ Execute Lokr calls │
   │ Append results     │
   │ Loop back to       │
   │ Analyzer (max 3x)  │
   └────────┬───────────┘
            ↓
┌─────────────────────────────────────┐
│ ACTION AGENT                        │
│ Input: Diagnosis + history +        │
│        safety_feedback (if revision)│
│                                     │
│ Generates: patch OR blockers        │
└──────────┬──────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ SAFETY AGENT                        │
│ Input: Proposed fix                 │
│ Output: Risk score + decision       │
│         + revision_suggestions      │
└──────────┬──────────────────────────┘
           ↓
    ┌──────┴───────┐
    │              │
  SAFE        UNSAFE
    │              │
    ↓          ┌───▼─────────────┐
    │          │ Revision Loop?  │
    │          └───┬──────┬──────┘
    │              │      │
    │            YES      NO
    │              │      │
    │              ↓      ↓
    │          [Action]  [Analyzer]
    │          (0.3x)    (fallback)
    │              │
    └──────┬───────┘
           ↓
┌─────────────────────────────────────┐
│ VALIDATOR AGENT                     │
│ (Optional)                          │
│ Input: Final fix                    │
│ Output: Test cases + checklists     │
└──────────┬──────────────────────────┘
           ↓
      📋 RESULT
```

### Agent Responsibilities

| Agent | Role | Key Constraint |
|-------|------|----------------|
| **Pre-Scan** | Deterministic regex scan for backdoors | Runs before LLM; findings are injected as mandatory context |
| **Analyzer** | Diagnoses issues, assesses readiness | Starts with minimal context; requests more via `lokr_requests`; raises `ValueError` on schema failure |
| **Action** | Generates fixes / identifies blockers | Reads safety feedback for targeted revisions; cross-references raw user input |
| **Safety** | Risk scoring, go/no-go decision | Provides `revision_suggestions` for fast-path Action revision; can't rubber-stamp |
| **Validator** | Validates fixes, generates checklists | Triggers revision loop on failure |

---

## 🔐 Pipeline Safety Guardrails

| Guardrail | Mechanism | Benefit |
|-----------|-----------|---------|
| **Schema Validation** | All agents raise `ValueError` on malformed JSON | No stub fallbacks, explicit errors |
| **Evidence Grounding** | Token-based matching handles LLM abbreviations; logs ratio | Visible grounding quality per run |
| **Soft-Fail Threshold** | Warns (not aborts) if <50% findings grounded; Safety is final judge | Allows imperfect-but-useful findings |
| **Loop Detection** | Safety↔Action: 3 iterations. Main: 25 iterations | Prevents infinite loops |
| **Token Budget** | Forensic logging warns if analyzer input > 8k tokens | Early warning of context bloat |
| **Context Growth Tracking** | `[FORENSIC]` logs track token delta per Lokr request | Visible efficiency gains |
| **Hard Blockers** | Security conditions hardcoded (auth removal, DB migrations) | LLM can't rubber-stamp |

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.10+** (Python 3.10 – 3.12 recommended)
- **Ollama** (for local privacy) OR any **OpenAI-compatible API**
- **Lokr (dev-oracle)** indexed on your project *(optional but recommended)*

### Installation

```bash
# Clone the repository with the Lokr engine bundled (Submodule)
git clone --recurse-submodules https://github.com/Anasmtaweh/Lokr-assistant.git
cd Lokr-assistant

# (Optional) If you forgot --recurse-submodules, run:
# git submodule update --init --recursive
```

### Running via Docker (Recommended)

The easiest way to run the assistant with all dependencies and the demo app mounted:

```bash
# Export your API Key if you plan to use a remote model
export API_KEY="your_api_key_here"

# Build and start the container
docker-compose up -d --build
```

The UI will be available at `http://localhost:8501`.

### Running Locally (Python Venv)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

You can start the UI using the provided helper script:

```bash
./start.sh
```

Or manually:

```bash
streamlit run app.py
```

> 💡 **Tip for Local Users:** If you are running the app locally, you can analyze your own codebase! Just change the "Project Directory" path in the UI sidebar to point to your local project folder and click **"Re-index Project"**. This will trigger the Lokr engine to extract ASTs and build the semantic graph for your code.

### 🌐 Running on Public Environments (Hugging Face Spaces)

If you are hosting or visiting Lokr Assistant on a public platform like Hugging Face Spaces:
- **Using Remote APIs:** If the space owner configured an `API_KEY` secret, it will auto-populate. **However, any user can simply delete the pre-filled key in the sidebar and paste their own API key** without affecting the space or other users.
- **Using Local Models (Ollama) Remotely:** A public space runs on a remote server. Using `http://localhost:11434` will try to connect to the space's server, not your personal computer. To connect a public space to *your* local Ollama:
  1. Expose your local Ollama port (11434) using a tool like [Ngrok](https://ngrok.com/).
  2. Paste your Ngrok URL into the **"Ollama Base URL"** field in the sidebar.
  3. Select **"Custom..."** from the model dropdown and type your model name (e.g., `qwen2.5-coder:7b`).

The UI will:
1. Auto-detect available Ollama models
2. Allow switching between local Ollama and remote APIs
3. Show live agent progress with `st.status` updates
4. Display forensic logs and token counts in expanders

### Run via CLI

```bash
# Repair mode (Local Ollama)
python main.py repair -c "your code" --model qwen2.5-coder:7b --api-url http://localhost:11434

# Repair mode (Remote OpenAI-compatible endpoint)
python main.py repair -c "your code" --model <model> --api-url <url> --api-key <key>

# Review mode
python main.py review -d "your diff" --model <model> --api-url <url>

# Prevent mode
python main.py prevent -c "your code" --model <model> --api-url <url>
```

> **Note:** Providing `--api-key` automatically selects the OpenAI-compatible provider (`--api-type openai`). Add `--project /path/to/project` to enable Lokr Graph-RAG context. You can also define variables in a `.env` file.

### Run as MCP Server (Model Context Protocol)

You can also run Lokr Assistant as an MCP server to integrate directly with IDEs and AI agent tools (Cursor, Claude Desktop, Antigravity):

```bash
python assistant_mcp_server.py
```

Exposes `run_repair`, `run_review`, `run_prevent`, and `check_task` tools over MCP stdio transport.

**Configurable Environment Variables (via shell or `.env`):**
- `API_KEY`: API key for remote LLM providers.
- `MODEL`: Model name (default: `accounts/fireworks/models/glm-5p3-flash`).
- `API_URL`: Base API URL (default: `https://api.fireworks.ai/inference/v1`).
- `API_TYPE`: `openai` or `ollama` (default: `openai`).
- `LOKR_PROJECT_PATH`: Target project directory (defaults to `./lokr-demo-app`).

---

## 🛠️ Tech Stack

- **LLM Backend:** Dual-support for [Ollama](https://ollama.com) (local/private) and **OpenAI-Compatible APIs** via UI toggle.
- **Code Intelligence:** [Lokr](https://github.com/Anasmtaweh/lokr) (Bundled as a submodule)
  - **Parsing:** Tree-sitter (AST extraction for JS, TS, Python, etc.)
  - **Vector Search:** ChromaDB (Semantic node retrieval)
  - **Graph Engine:** NetworkX (Dependency graph + topological sorting)
- **UI:** [Streamlit](https://streamlit.io) with real-time progress tracking
- **Language:** Python 3.8+

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Questions or Feedback?** Open an issue or submit a pull request.

</div>