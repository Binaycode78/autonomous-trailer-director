import json
from typing import Optional
from .client import LLMResponse, LLMClient

class MockClient:
    def __init__(self):
        self.call_count = 0
        
    def complete(self, system_prompt: str, user_prompt: str, context: Optional[dict] = None) -> LLMResponse:
        self.call_count += 1
        combined_prompt = f"{system_prompt} {user_prompt}".lower()
        
        response_content = "{}"
        
        if 'story_map' in combined_prompt:
            response_content = json.dumps({
                "title": "The Salt Coast",
                "characters": [
                    {"name": "Elena", "role": "protagonist", "description": "", "relationships": []},
                    {"name": "Mara", "role": "supporting", "description": "", "relationships": []},
                    {"name": "Dorian", "role": "supporting", "description": "", "relationships": []},
                    {"name": "Petra", "role": "supporting", "description": "", "relationships": []},
                    {"name": "Kade", "role": "supporting", "description": "", "relationships": []},
                    {"name": "Nessa", "role": "supporting", "description": "", "relationships": []}
                ],
                "relationships": [],
                "events": [],
                "emotional_arc": [],
                "spoiler_map": {
                    "protected_facts": ["Dorian Salt is Elena's biological father", "The missing child narrative is a false memory implanted by Petra"],
                    "spoiler_scenes": ["scene_09", "scene_11"],
                    "spoiler_dialogue": [],
                    "spoiler_definition": "Any reveal of Dorian's true identity or the truth about the missing child."
                },
                "sensitive_content": {},
                "themes": []
            })
        elif 'audience_promise_family' in combined_prompt:
            response_content = json.dumps({
                "statement": "A mystery that brings a family closer together — warmth, suspense, and heart",
                "emotional_journey": [
                    "Hook: A child's curiosity draws us into a coastal secret", 
                    "Tension: The lighthouse holds answers Elena fears", 
                    "Emotional Pull: A mother's love tested by the past", 
                    "CTA: Some secrets were meant to be found"
                ],
                "tone": "warm and suspenseful",
                "what_audience_will_expect": "A family-friendly mystery with heart and stakes",
                "what_is_protected": ["Dorian's true identity", "The truth about the missing child"]
            })
        elif 'audience_promise_young_adult' in combined_prompt:
            response_content = json.dumps({
                "statement": "Who do you trust when the past keeps secrets?", 
                "emotional_journey": [
                    "Hook: Elena returns to a town that remembers too much", 
                    "Tension: Kade knows something. Petra knows more.", 
                    "Emotional Pull: Identity, loyalty, and what we inherit", 
                    "CTA: The truth doesn't wait"
                ], 
                "tone": "urgent and character-driven", 
                "what_audience_will_expect": "A fast-paced character mystery with conflict and identity", 
                "what_is_protected": ["Dorian's true identity", "The false memory revelation"]
            })
        elif 'audience_promise_dialect' in combined_prompt:
            response_content = json.dumps({
                "statement": "A tense family mystery told in a familiar voice", 
                "emotional_journey": [
                    "Hook: The salt coast calls Elena home", 
                    "Tension: The sea keeps the secrets of those who stay", 
                    "Emotional Pull: Some ties run deeper than blood", 
                    "CTA: The tide always turns"
                ], 
                "tone": "authentic and emotionally resonant", 
                "what_audience_will_expect": "A story that speaks their language and understands their world", 
                "what_is_protected": ["Dorian's true identity", "The false memory revelation"]
            })
        elif 'segment_selection_family' in combined_prompt:
            response_content = json.dumps([
                {"segment_id": "seg_1", "source_in": "00:00:10.000", "source_out": "00:00:55.000", "video": "scene_01", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_2", "source_in": "00:04:20.000", "source_out": "00:05:00.000", "video": "scene_04", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_3", "source_in": "00:08:15.000", "source_out": "00:08:55.000", "video": "scene_07", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_4", "source_in": "00:10:30.000", "source_out": "00:11:10.000", "video": "scene_10", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_5", "source_in": "00:11:45.000", "source_out": "00:12:00.000", "video": "scene_12", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []}
            ])
        elif 'segment_selection_young_adult' in combined_prompt:
            response_content = json.dumps([
                {"segment_id": "seg_1", "source_in": "00:02:40.000", "source_out": "00:03:20.000", "video": "scene_03", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_2", "source_in": "00:05:30.000", "source_out": "00:06:00.000", "video": "scene_05", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_3", "source_in": "00:06:05.000", "source_out": "00:06:35.000", "video": "scene_06", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_4", "source_in": "00:09:00.000", "source_out": "00:09:40.000", "video": "scene_08", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_5", "source_in": "00:10:30.000", "source_out": "00:11:00.000", "video": "scene_10", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []}
            ])
        elif 'segment_selection_dialect' in combined_prompt:
            response_content = json.dumps([
                {"segment_id": "seg_1", "source_in": "00:01:30.000", "source_out": "00:02:10.000", "video": "scene_02", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_2", "source_in": "00:08:15.000", "source_out": "00:08:55.000", "video": "scene_07", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_3", "source_in": "00:10:30.000", "source_out": "00:11:00.000", "video": "scene_10", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []},
                {"segment_id": "seg_4", "source_in": "00:11:45.000", "source_out": "00:12:00.000", "video": "scene_12", "audio": "dialogue_and_music", "subtitle": "test", "subtitle_track": "standard", "reason": "reason", "evidence": [], "risk_flags": []}
            ])
        elif 'verify_spoiler' in combined_prompt:
            response_content = json.dumps({"result": "PASS", "spoiler_segments": [], "warnings": []})
        elif 'verify_bias' in combined_prompt:
            response_content = json.dumps({"result": "PASS", "bias_flags": [], "warnings": ["Ensure dialect usage reflects cultural pride, not novelty"]})
        else:
            response_content = "{}"

        return LLMResponse(content=response_content, model="mock-model", usage_tokens=0, cost_usd=0.0)
