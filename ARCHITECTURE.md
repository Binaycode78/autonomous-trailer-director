# Architecture Note — Autonomous Trailer Director

## Overview

The Autonomous Trailer Director is a multi-agent pipeline that analyzes an episode package and produces three validated, audience-specific trailer Edit Decision Lists (EDLs). The system is designed around five principles: **creative planning**, **hard constraint enforcement**, **multimodal grounding**, **verifiable decisions**, and **targeted recovery**.

---

## System Architecture

```
Episode Package (JSON)
        │
        ▼
┌─────────────────┐
│  INGESTION      │  Loads + validates episode, policies, contracts, profiles
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  ANALYSIS LAYER (parallel agents)        │
│                                          │
│  StoryAgent      → story_map.json        │
│  ConstraintAgent → constraint_map.json   │
│  AudienceAgent   → per-audience promises │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  PLANNING LAYER (per audience)           │
│                                          │
│  PromisePlanner  → creative brief        │
│  SegmentSelector → candidate scenes      │
│  NarrativeArc   → ordered mini-story    │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  VERIFICATION PIPELINE (8 checkers)      │
│                                          │
│  SourceChecker       SpoilerChecker      │
│  RightsChecker       RatingsChecker      │
│  TruthChecker        BiasChecker         │
│  AccessibilityChecker BudgetChecker      │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  REPAIR ENGINE                           │
│  RepairAgent → replace or reject segs   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  OUTPUT LAYER                            │
│  3× TrailerEDL (JSON)                    │
│  story_map.json, constraint_map.json     │
│  validation_report.md, decision_log.jsonl│
└─────────────────────────────────────────┘
```

---

## Planning and Memory

### Story Agent
Builds a structured `StoryMap` containing characters, relationships, events, emotional arc, and a `SpoilerMap`. The spoiler definition used is:

> *"A spoiler is a narrative fact that materially changes how a viewer understands the ending, twist, or resolution — if learned before watching. It includes character identity reveals, false-reality reveals, and death reveals."*

This definition is applied to classify scenes and dialogue lines, and the output spoiler map drives constraint rules.

### Constraint Agent
Converts human-readable policies and contracts into **machine-executable rules** (`ConstraintRule` objects with `applies_to`, `action`, `audiences`, and `active` fields). This is the key difference from treating policies as "a prompt paragraph" — constraints are structured data that checkers operate on deterministically.

**Prompt injection detection**: The agent scans all source material (scene descriptions, contracts) for injection phrases (`ignore contract`, `disregard rule`, `override policy`, `forget previous`). Detected injections are logged and the constraint is enforced regardless.

### Audience Agent
Builds a structured `AudiencePromise` with an explicit 4-step emotional journey (Hook → Tension → Emotional Pull → CTA) before any segment is selected. This prevents the system from just assembling high-engagement clips — every segment must serve the promise.

**Bias detection built-in**: If a historically high-performing scene is a spoiler, the agent flags this conflict and excludes it from selection guidance. The audience profile's `bias_warning` field is surfaced as a warning in the decision log.

---

## Multimodal Grounding

The system grounds all decisions in the episode's structured data:
- **Timecodes**: Every segment has `source_in` / `source_out` validated against the scene's actual bounds
- **Scene descriptions**: All story map claims are checked against scene text
- **Dialogue**: Quotable moments are verified against `dialogue.json`
- **Subtitles**: Dialect tracks are cross-referenced for meaning changes (handled by surprise event handler)

The `SourceChecker` runs as the first verification step and **hard-rejects** any segment referencing a non-existent scene or out-of-bounds timecode. This directly catches LLM hallucinations.

---

## Constraint Reasoning

Constraints are **decision rules, not prompt text**:

```json
{
  "rule_id": "R-001",
  "type": "spoiler",
  "applies_to": ["scene_09", "scene_11"],
  "action": "EXCLUDE",
  "audiences": [],
  "active": true
}
```

Each checker receives the `ConstraintMap` and evaluates segments against the rule set programmatically. A rule can be deactivated (e.g., when a contract expires) and a new rule added — this is the mechanism for targeted replanning.

---

## Verification

The verification pipeline is designed to **genuinely reject** bad creative choices:

| Checker | Failure Severity | What It Catches |
|---------|-----------------|-----------------|
| `SourceChecker` | HARD | Non-existent scenes or timecodes |
| `SpoilerChecker` | HARD | Scenes/dialogue in spoiler map |
| `RightsChecker` | HARD | Actor/music/territory violations |
| `RatingsChecker` | HARD | Age/content policy violations |
| `TruthChecker` | SOFT/HARD | Manufactured claims |
| `BiasChecker` | SOFT | Stereotype usage |
| `AccessibilityChecker` | SOFT | Subtitle/audio issues |
| `BudgetChecker` | HARD | Over-budget |

**Creative generation and verification are separate**: The planning agents and verification checkers are independent modules. The checkers do not know how segments were selected — they evaluate the proposal on its merits alone.

---

## Failure Recovery

The `RepairAgent` applies a structured repair strategy:
1. SOFT failures → accept with warning, log for human review
2. HARD failures → find replacement scene (emotionally compatible, constraint-compliant)
3. Replacement found → swap segment, log the replacement with full evidence
4. No replacement → mark segment `UNRESOLVED`, set `human_approval_required=True`

The system **never silently passes** a HARD failure. A `FAIL_UNRESOLVED` status is a valid, documented outcome.

---

## Replanning After Changes

The `SurpriseEventHandler` implements **targeted replanning**:
- When music rights expire → identify only the segments using that track → flag only those → re-verify only the affected trailers
- When a scene is reclassified as spoiler → add an EXCLUDE rule → flag segments in all trailers using that scene → re-verify only those

This is different from rebuilding all three trailers: the change log records exactly which rules changed, which segments are affected, and which trailers need re-verification.

---

## Human Control Points

The system explicitly identifies decisions requiring human oversight:
- Any `FAIL_UNRESOLVED` trailer
- Segments where no valid replacement was found
- Dialect subtitle changes that alter character relationships
- Clickbait requests that cannot be verified against episode
- Bias detections in audience data

These are surfaced in `validation_report.md` and in each trailer's `validation.human_approvals_required` list.

---

## LLM Client Architecture

```
LLMClient (Protocol)
    ├── GroqClient         Real API (llama-3.3-70b-versatile → fallback: llama-3.1-8b-instant)
    ├── MockClient         Deterministic responses, zero cost, no API key
    └── ReplayClient       Plays back recorded real responses
```

All LLM calls go through `BaseAgent._call_llm()` which:
1. Builds the prompt with context
2. Calls the client
3. Tracks cost via `CostTracker`
4. Logs the decision via `DecisionLogger`
5. Parses JSON from the response (handles markdown code blocks)

---

## Observability

Every decision is recorded in `decision_log.jsonl`:
```json
{
  "timestamp": "2026-09-28T13:00:00Z",
  "agent": "SegmentSelector",
  "action": "scene_rejected_despite_high_engagement",
  "reasoning": "scene_09 is in historic top performers but is a major spoiler. Excluded per constraint R-001.",
  "evidence": ["scene:09", "rule:R-001", "spoiler_map"],
  "cost_usd": 0.002,
  "llm_used": "llama-3.3-70b-versatile",
  "affected_trailers": ["family_v1"]
}
```

Surprise events are also logged with before/after state, affected rules, and affected segments.

---

## Budget Management

The `CostTracker` wraps all LLM calls and:
- Tracks per-agent costs
- Raises `BudgetExceededError` if the limit is hit
- Triggers automatic fallback to mock mode
- Reports percent of budget used

Default budget: **$2.00 USD** (configurable via `--budget` flag).
