from src.agents.audience_agent import AudiencePromise
from src.ingestion.loader import EpisodePackage
from src.verification.source_checker import RiskFlag

def check_truth(creative_brief: str, audience_promise: AudiencePromise, episode: EpisodePackage, story_map) -> list[RiskFlag]:
    flags = []
    
    # Check what_audience_will_expect against episode scenes
    has_action = any("action" in s.get("tags", []) for s in episode.scenes)
    
    for claim in audience_promise.what_audience_will_expect:
        claim_lower = claim.lower()
        if "action sequences" in claim_lower and not has_action:
            flags.append(RiskFlag("TruthChecker", "HARD FAIL", "Promised action sequences but episode has none"))
            
    return flags
