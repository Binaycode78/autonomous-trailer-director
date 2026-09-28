from pydantic import BaseModel, Field
from typing import Optional

class SceneModel(BaseModel):
    scene_id: str
    timecode_in: str  # HH:MM:SS.mmm
    timecode_out: str
    description: str
    characters: list[str]
    location: str
    emotional_tags: list[str]
    music_track: str
    dialogue_lines: list[str]
    is_spoiler: bool
    sensitive_content: list[str]

class DialogueLine(BaseModel):
    line_id: str
    scene_id: str
    speaker: str
    timecode: str
    text_standard: str
    text_mariner: str
    text_highland: str
    emotional_tone: str
    is_quotable: bool
    is_spoiler: bool

class EpisodeMeta(BaseModel):
    title: str
    episode_number: int
    season: int
    total_duration_seconds: int
    language: str
    dialect_tracks: list[str]
    genre: str
    synopsis: str
    content_advisory: list[str]

class EpisodePackage(BaseModel):
    meta: EpisodeMeta
    scenes: list[SceneModel]
    dialogue: list[DialogueLine]
