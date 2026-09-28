# Autonomous Trailer Director

> An agentic AI system that plans three audience-specific trailers from one episode while protecting story truth, viewer safety, cultural respect and contractual rights.

## Quick Start

### Zero API Key (Mock Mode) — for evaluators

```bash
# Clone / extract the project
cd d:/stage_project

# Install dependencies
pip install -r requirements.txt

# Run with mock LLM (no API key needed)
python -m src.main --episode data/ --mode mock --output sample_run/
```

### Real LLM (Groq API)

```bash
# Set your Groq API key
set GROQ_API_KEY=your_key_here   # Windows
export GROQ_API_KEY=your_key_here  # Unix

# Run with real LLM
python -m src.main --episode data/ --mode real --output out/
```

### Surprise Event Simulation

```bash
# Simulate music rights expiring
python -m src.main --episode data/ --mode mock --event music_rights_expired --output out/

# Simulate spoiler reclassification
python -m src.main --episode data/ --mode mock --event spoiler_reclassified --output out/

# Simulate clickbait request
python -m src.main --episode data/ --mode mock --event clickbait_requested --output out/

# Simulate model unavailable
python -m src.main --episode data/ --mode mock --event model_unavailable --output out/

# Simulate bias detected in audience data
python -m src.main --episode data/ --mode mock --event bias_detected --output out/
```

### FastAPI Server (optional)

```bash
uvicorn src.api:app --reload
# API docs at http://localhost:8000/docs
```

### Run All Tests

```bash
pytest tests/ -v --tb=short
```

## CLI Reference

```
python -m src.main [OPTIONS]

Options:
  -e, --episode TEXT     Episode package directory       [default: data/]
  -o, --output TEXT      Output directory                [default: sample_run/]
  -m, --mode TEXT        LLM mode: mock | real | replay  [default: mock]
  --model TEXT           Groq model name                 [default: llama-3.3-70b-versatile]
  --event TEXT           Surprise event to inject
  --replay-dir TEXT      Recorded responses directory (replay mode)
  --budget FLOAT         Max cost in USD                 [default: 2.0]
  -v, --verbose          Verbose output
```

## Outputs (in output directory)

| File | Description |
|------|-------------|
| `story_map.json` | Characters, events, spoiler map, sensitive content |
| `constraint_map.json` | Testable rules from policies and contracts |
| `family_trailer.json` | Family audience EDL with full validation |
| `young_adult_trailer.json` | Young adult EDL |
| `dialect_region_trailer.json` | Dialect-region EDL |
| `validation_report.md` | Human-readable validation summary |
| `decision_log.jsonl` | Full audit trail of all decisions |

## Episode: "The Salt Coast"

The system uses a synthetic 12-minute episode: a coastal family mystery drama with:
- 12 scenes with exact timecodes
- 30 dialogue lines with standard + 2 dialect tracks (Mariner, Highland)
- 4 main characters, 3 supporting
- 2 major spoilers (scene_09, scene_11)
- 3 music tracks with different rights scopes
- Complex actor and territory contracts

## Project Structure

```
src/
├── main.py              CLI entry point
├── api.py               FastAPI wrapper
├── orchestrator.py      Pipeline coordinator
├── agents/              Analysis + planning agents
├── verification/        8-checker verification pipeline
├── events/              Surprise event handler
├── ingestion/           Episode package loader
├── llm/                 Groq + mock + replay clients
├── models/              Pydantic data models
└── utils/               Timecode, cost, logging

data/                    Synthetic episode package
tests/                   Automated test suite
sample_run/              Pre-generated output files
```
