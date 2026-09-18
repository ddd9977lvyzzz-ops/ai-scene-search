"""Central feature registry for query understanding, retrieval, ranking and product debugging.

The important design rule is that not every feature belongs in one vector. Exact facts and
hard constraints stay structured; semantic/tone/theme signals are vector-friendly; safety
facts retain provenance and confidence.
"""
from __future__ import annotations

FEATURE_SCHEMA_VERSION = '3.0'

FEATURE_GROUPS = {
    'hard_metadata': [
        'content_type', 'language', 'country', 'runtime_minutes', 'release_year',
        'platform_availability',
    ],
    'scene_context': [
        'companions', 'occasion', 'time_context', 'session_length', 'attention_level',
        'background_friendly', 'bingeability',
    ],
    'affect': [
        'light', 'relaxing', 'healing', 'funny', 'romantic', 'emotional', 'tense',
        'exciting', 'scary', 'thought_provoking',
    ],
    'narrative': [
        'pace', 'cognitive_load', 'plot_density', 'twist_intensity', 'dialogue_density',
        'worldbuilding', 'episodicness',
    ],
    'relationships_themes': [
        'romantic', 'friendship', 'family', 'workplace', 'coming_of_age', 'crime',
        'adventure', 'history', 'food', 'music',
    ],
    'tone_style': [
        'sweet', 'gentle', 'playful', 'warm', 'realistic', 'bittersweet', 'dark',
        'quirky', 'stylized',
    ],
    'risk': [
        'fear_or_horror', 'violence_possible', 'mature_rating', 'social_embarrassment',
        'emotionally_heavy', 'childish', 'death_or_grief', 'infidelity',
        'abusive_relationship', 'animal_harm',
    ],
    'plot_facts': [
        'no_character_death', 'happy_ending', 'no_animal_harm', 'no_infidelity',
        'no_gore', 'no_jump_scares', 'no_sexual_content', 'family_safe',
        'closed_ending', 'romance_central', 'friendship_central', 'career_central',
    ],
    'discovery': [
        'popularity_bucket', 'mainstreamness', 'novelty', 'freshness', 'rating_score',
        'rating_count',
    ],
    'evidence_quality': [
        'data_quality_score', 'tag_confidence', 'understanding_confidence',
        'evidence_source', 'spoiler_level',
    ],
}

FEATURE_ROLES = {
    'structured_filter': FEATURE_GROUPS['hard_metadata'] + FEATURE_GROUPS['risk'] + FEATURE_GROUPS['plot_facts'],
    'sparse_retrieval': FEATURE_GROUPS['relationships_themes'] + FEATURE_GROUPS['tone_style'],
    'dense_retrieval': FEATURE_GROUPS['affect'] + FEATURE_GROUPS['narrative'] + FEATURE_GROUPS['relationships_themes'] + FEATURE_GROUPS['tone_style'],
    'ranking': FEATURE_GROUPS['scene_context'] + FEATURE_GROUPS['affect'] + FEATURE_GROUPS['narrative'] + FEATURE_GROUPS['relationships_themes'] + FEATURE_GROUPS['tone_style'] + FEATURE_GROUPS['plot_facts'] + FEATURE_GROUPS['discovery'],
    'grounding_only': FEATURE_GROUPS['evidence_quality'],
}


def public_feature_schema() -> dict:
    return {
        'version': FEATURE_SCHEMA_VERSION,
        'principle': '硬事实结构化；语义偏好向量化；风险与剧情事实必须保留证据和置信度。',
        'groups': FEATURE_GROUPS,
        'roles': FEATURE_ROLES,
    }
