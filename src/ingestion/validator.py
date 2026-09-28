"""
Episode Package Validator
=========================
Validates scene timecodes, scene ID consistency, dialogue cross-references, and episode metadata.
"""
from typing import Any
from src.utils.timecode import validate_timecode_format, duration_seconds
from src.ingestion.loader import EpisodePackage


def validate_episode_package(pkg: EpisodePackage) -> dict[str, list[str]]:
    """
    Validates episode metadata, scenes, and dialogue.
    Returns a dict with 'errors' and 'warnings' lists.
    """
    errors: list[str] = []
    warnings: list[str] = []

    scene_ids = set()
    total_scene_dur = 0.0

    for i, scene in enumerate(pkg.scenes):
        s_id = scene.get("scene_id")
        start = scene.get("start_time") or scene.get("timecode_in")
        end = scene.get("end_time") or scene.get("timecode_out")

        if not s_id:
            errors.append(f"Scene at index {i} missing scene_id")
            continue

        scene_ids.add(s_id)

        if not start or not validate_timecode_format(start):
            errors.append(f"Scene {s_id} invalid start timecode format: {start}")
        if not end or not validate_timecode_format(end):
            errors.append(f"Scene {s_id} invalid end timecode format: {end}")

        if start and end and validate_timecode_format(start) and validate_timecode_format(end):
            dur = duration_seconds(start, end)
            if dur <= 0:
                errors.append(f"Scene {s_id} has negative or zero duration")
            total_scene_dur += dur

    # Check dialogue scene references
    for i, line in enumerate(pkg.dialogue):
        s_id = line.get("scene_id")
        if s_id and s_id not in scene_ids:
            errors.append(f"Dialogue line {i} references missing scene_id: {s_id}")

    # Check total duration
    meta_dur = pkg.meta.get("total_duration_seconds", 0)
    if meta_dur > 0 and abs(total_scene_dur - meta_dur) > 60:
        warnings.append(
            f"Total scene duration ({total_scene_dur:.1f}s) differs from meta duration ({meta_dur}s)"
        )

    return {"errors": errors, "warnings": warnings}
