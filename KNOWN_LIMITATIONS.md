# Known Limitations

## What This System Does Not Do

### 1. Real Video Analysis
The system works entirely from structured JSON (scene descriptions, dialogue, timecodes). It does not analyze actual video frames, audio waveforms, or visual content. A production system would add:
- Vision model frame sampling per scene
- Audio emotion detection
- Face detection for cast verification

**Human decision required**: Visual suitability (on-screen violence intensity, visual pacing) must be reviewed by a human editor.

### 2. Real Video Rendering
The output is an Edit Decision List (EDL) — a precise JSON blueprint. Rendering requires a separate tool (e.g., FFmpeg, Adobe Premiere, DaVinci Resolve). The EDL contains all timecodes, audio choices, subtitle tracks, and text cards needed for a human or automated editor to produce the final video.

### 3. Actual Rights Database Integration
Contracts are loaded from a JSON file. A production system would integrate with:
- A rights management database (e.g., FilmTrack, Rightsline)
- Real-time territory restriction APIs
- Automated contract expiry monitoring

**Human decision required**: Any borderline rights case must be reviewed by a legal team before production use.

### 4. Cultural Authenticity Validation
The `BiasChecker` detects stereotype language patterns in creative briefs. It does NOT:
- Validate that dialect translations are linguistically accurate
- Assess cultural appropriateness with community consultation

**Human decision required**: All dialect-region trailer plans require review by a cultural consultant from the represented community before use.

### 5. Live Audience Feedback
The system uses static audience profiles from JSON files. It does not:
- Run A/B tests on actual viewers
- Adapt in real-time to viewing data
- Query live engagement APIs

### 6. Multi-Episode Context
The system analyzes one episode at a time. It does not track series-level spoiler arcs, season-wide character development, or cross-episode contracts.

### 7. Scale Limitations
The pipeline runs sequentially per audience in the current implementation. At production scale:
- Parallel async execution would be needed per audience
- The cost tracker would need a distributed store (Redis, database)
- LLM prompt caching would be critical for cost efficiency

The component most likely to fail first at scale: the **LLM call budget tracker** — it is in-memory and not distributed.

---

## Decisions That Must Remain With Humans

| Decision | Why Human Required |
|----------|--------------------|
| Final rights approval for any segment | Legal liability |
| Cultural/dialect content review | Community representation |
| Spoiler judgment for ambiguous scenes | Narrative interpretation is subjective |
| Clickbait borderline cases | Brand and editorial judgment |
| `FAIL_UNRESOLVED` trailer release | System has flagged it cannot auto-fix |
| Trailer release in restricted territories | Territory law may change faster than contracts |
| Bias warning resolution | Requires sociological/community expertise |
| Any `human_approval_required: true` segment | System has explicitly flagged human review |

---

## Known Risks

- **Mock responses**: The mock LLM client returns deterministic responses that may not reflect real model behavior. Real-mode testing with a Groq API key is recommended before production.
- **Prompt injection**: Detection is keyword-based. A sophisticated adversary using paraphrased injection phrases may evade detection.
- **Dialect translations**: The synthetic dialect dialogue was created for demonstration. Real productions must use verified translators.
- **Timecode precision**: The synthetic episode uses approximate timecodes. Real episode analysis would require frame-accurate timecode extraction.
