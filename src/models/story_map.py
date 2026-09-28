from pydantic import BaseModel
from typing import Optional

class Character(BaseModel):
    name: str
    role: str  # 'protagonist', 'antagonist', 'supporting'
    description: str
    relationships: list[str]

class StoryEvent(BaseModel):
    event_id: str
    scene_id: str
    description: str
    emotional_significance: str
    is_spoiler: bool
    spoiler_reason: Optional[str] = None

class SpoilerMap(BaseModel):
    protected_facts: list[str]  # Plain language facts that must not be revealed
    spoiler_scenes: list[str]  # scene_ids
    spoiler_dialogue: list[str]  # line_ids
    spoiler_definition: str  # How the system defines a spoiler

class StoryMap(BaseModel):
    title: str
    characters: list[Character]
    relationships: list[dict]
    events: list[StoryEvent]
    emotional_arc: list[str]
    spoiler_map: SpoilerMap
    sensitive_content: dict  # {scene_id: [tags]}
    themes: list[str]

    @property
    def spoiler_scenes(self) -> list[str]:
        return self.spoiler_map.spoiler_scenes if self.spoiler_map else []

    @property
    def spoiler_dialogue(self) -> list[str]:
        return self.spoiler_map.spoiler_dialogue if self.spoiler_map else []
