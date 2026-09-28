"""
Timecode utilities for parsing, validating, and computing durations.
Format: HH:MM:SS.mmm
"""
import re
from typing import Optional

def parse_timecode(tc: str) -> float:
    """Parse HH:MM:SS.mmm to total seconds (float)."""
    parts = tc.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid timecode format: {tc}")
    
    hours = float(parts[0])
    minutes = float(parts[1])
    seconds = float(parts[2])
    
    return (hours * 3600) + (minutes * 60) + seconds

def seconds_to_timecode(seconds: float) -> str:
    """Convert total seconds to HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def duration_seconds(tc_in: str, tc_out: str) -> float:
    """Return duration in seconds between two timecodes."""
    return parse_timecode(tc_out) - parse_timecode(tc_in)

def validate_timecode_exists(tc_in: str, tc_out: str, scene) -> tuple[bool, str]:
    """Check if the timecode range falls within a scene's bounds.
    Returns (is_valid, error_message)"""
    try:
        in_sec = parse_timecode(tc_in)
        out_sec = parse_timecode(tc_out)
        scene_in_sec = parse_timecode(scene.start_time)
        scene_out_sec = parse_timecode(scene.end_time)
        
        if in_sec < scene_in_sec or out_sec > scene_out_sec:
            return False, f"Timecode range {tc_in}-{tc_out} outside scene bounds {scene.start_time}-{scene.end_time}"
        
        if in_sec >= out_sec:
            return False, f"Invalid timecode range: in {tc_in} >= out {tc_out}"
            
        return True, ""
    except Exception as e:
        return False, str(e)

def validate_timecode_format(tc: str) -> bool:
    """Validate HH:MM:SS.mmm format."""
    pattern = r"^\d{2}:\d{2}:\d{2}\.\d{3}$"
    return bool(re.match(pattern, tc))
