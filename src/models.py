from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class SceneProfile:
    # Context / hard facts
    companions: Optional[str] = None
    scene: Optional[str] = None
    content_types: list[str] = field(default_factory=list)
    runtime_max: Optional[int] = None
    year_min: Optional[int] = None
    platforms: list[str] = field(default_factory=list)
    language: Optional[str] = None

    # Positive intent. required_genres are treated as strict when explicitly stated.
    genres: list[str] = field(default_factory=list)
    required_genres: list[str] = field(default_factory=list)
    relationship_focus: list[str] = field(default_factory=list)
    required_signals: list[str] = field(default_factory=list)  # strong non-genre intent: funny / fast / gentle ...
    audience_preferences: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)
    tone_preferences: list[str] = field(default_factory=list)
    pace_preferences: list[str] = field(default_factory=list)
    cognitive_load: Optional[str] = None
    popularity_preference: Optional[str] = None  # niche / balanced / mainstream
    quality_preference: Optional[str] = None     # acclaimed / any

    # Safety / dislikes
    avoid_genres: list[str] = field(default_factory=list)
    avoid_risks: list[str] = field(default_factory=list)

    # Discovery controls
    exploration_mode: str = 'precise'           # precise / balanced / explore
    exploration_strength: float = 0.0            # 0..1, never overrides hard constraints
    surprise_preferences: list[str] = field(default_factory=list)
    spoiler_tolerance: str = 'spoiler_free'

    # Traceability
    source_reference: Optional[str] = None
    confidence: float = 0.0
    conflicts: list[str] = field(default_factory=list)

    def merge(self, patch: 'SceneProfile') -> 'SceneProfile':
        scalar_fields = [
            'companions', 'scene', 'cognitive_load', 'runtime_max', 'year_min',
            'language', 'source_reference', 'popularity_preference',
            'quality_preference', 'spoiler_tolerance',
        ]
        for name in scalar_fields:
            value = getattr(patch, name)
            if value not in (None, ''):
                setattr(self, name, value)

        list_fields = [
            'moods', 'content_types', 'genres', 'required_genres',
            'relationship_focus', 'required_signals', 'audience_preferences', 'tone_preferences', 'pace_preferences',
            'surprise_preferences', 'avoid_genres', 'avoid_risks', 'platforms',
        ]
        for name in list_fields:
            incoming = getattr(patch, name)
            if incoming:
                current = getattr(self, name)
                for x in incoming:
                    if x not in current:
                        current.append(x)

        # Exploration is an explicit mode switch, not an additive preference.
        if patch.exploration_mode != 'precise' or patch.exploration_strength > 0:
            self.exploration_mode = patch.exploration_mode
            self.exploration_strength = patch.exploration_strength
        if patch.conflicts:
            self.conflicts = patch.conflicts
        self.confidence = max(self.confidence, patch.confidence)
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Candidate:
    content_id: str
    title: str
    content_type: str
    release_year: Optional[int]
    runtime_minutes: Optional[int]
    genres: list[str]
    description: str
    scene_tags: list[str]
    emotion_tags: list[str]
    watching_tags: list[str]
    risk_tags: list[str]
    cognitive_load: Optional[str]
    platforms: list[str]
    poster_url: Optional[str]

    audience_tags: list[str] = field(default_factory=list)
    pace_tags: list[str] = field(default_factory=list)
    relationship_tags: list[str] = field(default_factory=list)
    theme_tags: list[str] = field(default_factory=list)
    tone_tags: list[str] = field(default_factory=list)
    surprise_tags: list[str] = field(default_factory=list)
    content_facts: dict[str, Any] = field(default_factory=dict)
    risk_notes: list[dict[str, Any]] = field(default_factory=list)
    surprise_notes: list[dict[str, Any]] = field(default_factory=list)
    popularity_value: Optional[float] = None
    popularity_bucket: Optional[str] = None
    rating_score: Optional[float] = None
    understanding_confidence: float = 0.0

    score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    retrieval_reasons: list[str] = field(default_factory=list)


@dataclass
class MemoryItem:
    memory_id: str
    text: str
    memory_type: str
    created_at: str
    evidence_strength: float = 0.5
    source: str = 'conversation'
    structured: dict[str, Any] = field(default_factory=dict)
