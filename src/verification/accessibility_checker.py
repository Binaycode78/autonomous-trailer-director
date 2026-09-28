from src.agents.planning.narrative_arc import TrailerEDL
from src.verification.source_checker import RiskFlag

def check_accessibility(trailer: TrailerEDL) -> list[RiskFlag]:
    flags = []
    
    for segment in trailer.segments:
        if not getattr(segment, "subtitle_track", None):
            flags.append(RiskFlag("AccessibilityChecker", "SOFT FAIL", f"Segment {segment.scene_id} missing subtitle_track"))
            
        # check audio cue only mock
        # flags.append(RiskFlag("AccessibilityChecker", "SOFT FAIL", "Segment depends on audio cues only"))
        
    for card in trailer.text_cards:
        if card.duration < 2.0:
            flags.append(RiskFlag("AccessibilityChecker", "SOFT FAIL", f"Text card {card.role} duration under 2 seconds"))
            
    return flags
