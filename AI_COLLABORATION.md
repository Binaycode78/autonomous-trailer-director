# AI Collaboration Note

## How AI Tools Were Used in This Project

This project was built with the assistance of Claude (Sonnet / Gemini Advanced) and follows the principle: **delegate useful work, then verify and challenge the output**.

---

## What AI Was Asked to Do

### 1. Code Generation
- **Task**: Generate complete Python module implementations for agents, checkers, data models, CLI, and FastAPI wrapper.
- **Guidance given**: Detailed specifications per file — inputs, outputs, error handling behavior, and design constraints.
- **Verification**: Each generated file was reviewed for:
  - Correct Pydantic v2 syntax (not v1 `@validator` patterns)
  - Proper use of `Protocol` for LLM abstraction
  - Consistent use of `DecisionLogger` and `CostTracker` in every agent

### 2. Synthetic Episode Creation
- **Task**: Generate a coherent 12-scene episode ("The Salt Coast") with exact timecodes, dialect dialogue, and strategically placed spoilers/sensitive content.
- **Verification**: Checked that:
  - Timecodes are contiguous and sum to ~720 seconds
  - scene_09 and scene_11 are the designated spoilers
  - Dialect translations feel culturally distinct rather than comic
  - The `is_spoiler` flags are correctly placed

### 3. Mock LLM Responses
- **Task**: Write deterministic JSON responses for each agent's LLM call type.
- **Verification**: Verified that mock responses for `audience_promise_family`, `segment_selection_family`, etc. are internally consistent — the promises match the selected scenes.

---

## Where AI Was Wrong or Needed Correction

### Hallucination: Scene References
In early drafts, the segment selector mock returned `scene_13` which doesn't exist in the 12-scene episode. This was caught by the `SourceChecker` test (`test_missing_scene.py`) and corrected — demonstrating that the verification pipeline catches AI errors.

**Lesson**: AI-suggested scene references must always be validated against the actual episode data. The `SourceChecker` is the primary defense against this.

### Dialect Representation
The initial AI draft of dialect dialogue used coastal stereotypes (e.g., excessive use of "arr", treating dialect as comedic). This was rejected and replaced with:
- Culturally grounded idioms ("the salt in me blood", "the tide always turns")
- Emotional weight equal to the standard English version
- No humorous framing of dialect-speaking characters

**Lesson**: Dialect content requires explicit cultural framing in the prompt. The `BiasChecker` was designed specifically to catch this class of error.

### Pydantic v1 Patterns
AI initially generated `@validator` decorators (Pydantic v1 style). These were corrected to `@field_validator` (Pydantic v2 style).

### Overly Broad Constraint Rules
An early draft of the `ConstraintAgent` generated a single `EXCLUDE all frightening content` rule with `applies_to: []` (all scenes). This was too broad — it needed to be scoped to specific scene IDs. The implementation was corrected to generate per-scene rules with explicit scene IDs.

---

## AI Collaboration Principles Applied

| Principle | How Applied |
|-----------|-------------|
| **Delegate, don't blindly accept** | Every AI output was reviewed against spec before inclusion |
| **Challenge the model** | When AI produced a spoiler-containing segment selection, it was flagged and the checker was built to catch it |
| **Verify generated code** | Tests were written explicitly to catch AI hallucination (test_missing_scene.py) |
| **Use AI for boilerplate, not judgment** | AI wrote the structure; the constraint logic and spoiler definitions were human-specified |
| **Document AI errors** | Hallucination examples above are real, not fabricated |

---

## Models Used

| Model | Purpose |
|-------|---------|
| Claude Sonnet (via Gemini Advanced) | Code generation, architecture design, documentation |
| `llama-3.3-70b-versatile` (Groq) | Runtime LLM for story/constraint/audience analysis |
| `llama-3.1-8b-instant` (Groq) | Fallback when primary model unavailable |
| Mock client | Zero-cost evaluation mode |
