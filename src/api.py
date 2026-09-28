"""
Autonomous Trailer Director — FastAPI Web API
=============================================

Provides a REST interface for the trailer director pipeline.

Endpoints:
  POST /run          - Run the full pipeline
  POST /event        - Inject a surprise event into a running session
  GET  /status/{id}  - Get status of a run
  GET  /trailers/{id}/family     - Get family trailer EDL
  GET  /trailers/{id}/young_adult
  GET  /trailers/{id}/dialect_region
  GET  /report/{id}  - Get validation report
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Autonomous Trailer Director API",
    description="Creates audience-specific trailer Edit Decision Lists from episode packages.",
    version="1.0.0",
)

# In-memory run registry (use a database in production)
_runs: dict[str, dict] = {}


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------

class RunRequest(BaseModel):
    episode_dir: str = "data/"
    output_dir: str = "sample_run/"
    mode: Literal["mock", "real", "replay"] = "mock"
    model: str = "llama-3.3-70b-versatile"
    event: Optional[str] = None
    replay_dir: Optional[str] = None
    budget_usd: float = 2.0


class EventRequest(BaseModel):
    run_id: str
    event_type: str
    parameters: dict = {}


class RunStatus(BaseModel):
    run_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    summary: Optional[dict] = None
    error: Optional[str] = None


# ------------------------------------------------------------------
# Background task
# ------------------------------------------------------------------

def _run_pipeline(run_id: str, request: RunRequest):
    """Execute the pipeline in the background."""
    from src.orchestrator import TrailerDirectorOrchestrator

    _runs[run_id]["status"] = "running"
    try:
        orchestrator = TrailerDirectorOrchestrator(
            data_dir=request.episode_dir,
            output_dir=request.output_dir,
            mode=request.mode,
            model=request.model,
            event=request.event,
            replay_dir=request.replay_dir,
            budget_limit=request.budget_usd,
        )
        summary = orchestrator.run()
        _runs[run_id]["status"] = "completed"
        _runs[run_id]["summary"] = summary
        _runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        _runs[run_id]["output_dir"] = request.output_dir
    except Exception as e:
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(e)
        _runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.error(f"[API] Run {run_id} failed: {e}")


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.post("/run", response_model=RunStatus, summary="Start a trailer generation run")
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    """
    Start the autonomous trailer director pipeline.
    Returns a run_id to poll for status.
    """
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc).isoformat()

    _runs[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "started_at": started_at,
        "completed_at": None,
        "summary": None,
        "error": None,
    }

    background_tasks.add_task(_run_pipeline, run_id, request)

    return RunStatus(run_id=run_id, status="queued", started_at=started_at)


@app.get("/status/{run_id}", response_model=RunStatus, summary="Get run status")
async def get_status(run_id: str):
    """Get the current status of a pipeline run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    run = _runs[run_id]
    return RunStatus(**run)


@app.get("/trailers/{run_id}/{audience}", summary="Get a trailer EDL")
async def get_trailer(
    run_id: str,
    audience: Literal["family", "young_adult", "dialect_region"],
):
    """Get a generated trailer EDL by run ID and audience."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    run = _runs[run_id]
    if run["status"] != "completed":
        raise HTTPException(
            status_code=202,
            detail=f"Run not completed yet. Status: {run['status']}",
        )

    output_dir = Path(run.get("output_dir", "sample_run/"))
    file_map = {
        "family": output_dir / "family_trailer.json",
        "young_adult": output_dir / "young_adult_trailer.json",
        "dialect_region": output_dir / "dialect_region_trailer.json",
    }
    trailer_file = file_map[audience]

    if not trailer_file.exists():
        raise HTTPException(status_code=404, detail=f"Trailer file not found: {trailer_file}")

    return FileResponse(str(trailer_file), media_type="application/json")


@app.get("/report/{run_id}", summary="Get validation report")
async def get_report(run_id: str):
    """Get the validation report markdown for a run."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    run = _runs[run_id]
    output_dir = Path(run.get("output_dir", "sample_run/"))
    report_file = output_dir / "validation_report.md"

    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not yet generated.")

    with open(report_file, encoding="utf-8") as f:
        content = f.read()

    return {"run_id": run_id, "report": content}


@app.post("/event", summary="Inject a surprise event")
async def inject_event(request: EventRequest):
    """
    Inject a surprise event into a completed run's trailers.
    Triggers targeted re-verification of affected segments.
    """
    if request.run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run '{request.run_id}' not found.")

    # For a real implementation this would load the saved state and re-run
    # For now, return a description of what would happen
    event_impacts = {
        "music_rights_expired": "Identifies segments using the expired track, flags for repair, re-verifies affected trailers only.",
        "spoiler_reclassified": "Adds scene to spoiler map, adds EXCLUDE rule, re-verifies all trailers for the scene.",
        "clickbait_requested": "TruthChecker evaluates the promise against episode facts. Rejects if misrepresenting.",
        "model_unavailable": "Switches to fallback model (llama-3.1-8b-instant). Logs model change.",
        "scene_hallucination": "SourceChecker rejects non-existent scene. Logs AI error. Triggers repair.",
        "bias_detected": "BiasChecker flags audience data. Adds warnings to affected trailers. Logs for human review.",
        "dialect_subtitle_changed": "Flags dialect-track segments for human cultural review. Updates story map.",
    }

    impact = event_impacts.get(request.event_type, "Unknown event type.")
    return {
        "run_id": request.run_id,
        "event_type": request.event_type,
        "parameters": request.parameters,
        "expected_impact": impact,
        "note": "Re-run with --event flag to see targeted replanning in action.",
    }


@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "service": "Autonomous Trailer Director API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
