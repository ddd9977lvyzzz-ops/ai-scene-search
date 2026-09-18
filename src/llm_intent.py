from __future__ import annotations

"""Optional LLM soft-intent enrichment.

The deterministic parser remains authoritative for hard constraints (format, required/avoided
genres, platform, runtime, year). If enabled, the model may only add *soft* scene/taste signals.
That separation is intentional: semantic understanding can improve recall without being allowed to
silently violate what the user explicitly asked for.
"""

import json
import os
from .models import SceneProfile

SOFT_SCHEMA = {
    'type':'object',
    'properties':{
        'companions':{'anyOf':[{'type':'string','enum':['solo','family','friends','couple']},{'type':'null'}]},
        'scene':{'anyOf':[{'type':'string','enum':['party','late_night','commute','weekend','meal']},{'type':'null'}]},
        'moods':{'type':'array','items':{'type':'string','enum':['light','relaxing','healing','funny','exciting','tense','thought_provoking','scary','romantic']}},
        'cognitive_load':{'anyOf':[{'type':'string','enum':['low','medium','high']},{'type':'null'}]},
        'relationship_focus':{'type':'array','items':{'type':'string','enum':['romantic','family','friendship']}},
        'tone_preferences':{'type':'array','items':{'type':'string','enum':['sweet','gentle','realistic','bittersweet','dark','playful','warm','quirky','stylized']}},
        'pace_preferences':{'type':'array','items':{'type':'string','enum':['slow','moderate','fast']}},
        'surprise_preferences':{'type':'array','items':{'type':'string','enum':['plot_reveal','worldbuilding','relationship_turns','comic_payoff','visual_set_piece','insight','fresh_premise']}},
        'popularity_preference':{'anyOf':[{'type':'string','enum':['niche','mainstream']},{'type':'null'}]},
        'quality_preference':{'anyOf':[{'type':'string','enum':['acclaimed','any']},{'type':'null'}]},
    },
    'required':['companions','scene','moods','cognitive_load','relationship_focus','tone_preferences','pace_preferences','surprise_preferences','popularity_preference','quality_preference'],
    'additionalProperties':False,
}

def enabled() -> bool:
    return os.getenv('OPENAI_INTENT_ENABLED','0').strip().lower() in {'1','true','yes'} and bool(os.getenv('OPENAI_API_KEY')) and bool(os.getenv('OPENAI_INTENT_MODEL'))

def enrich_soft_profile(text: str) -> SceneProfile | None:
    if not enabled():
        return None
    try:
        from openai import OpenAI
        client=OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_BASE_URL') or None)
        response=client.responses.create(
            model=os.environ['OPENAI_INTENT_MODEL'],
            instructions=(
                'You extract soft viewing-scene preferences from Chinese or English movie/TV requests. '
                'Do not infer hard constraints such as required genre, forbidden genre, platform, runtime, year, or content type. '
                'Only return a preference when the user text supports it; otherwise return null or an empty list. '
                'Do not broaden explicit negatives. Return JSON matching the schema.'
            ),
            input=text,
            text={'format':{'type':'json_schema','name':'scene_soft_intent','strict':True,'schema':SOFT_SCHEMA}},
        )
        data=json.loads(response.output_text)
        p=SceneProfile()
        p.companions=data.get('companions')
        p.scene=data.get('scene')
        p.moods=data.get('moods') or []
        p.cognitive_load=data.get('cognitive_load')
        p.relationship_focus=data.get('relationship_focus') or []
        p.tone_preferences=data.get('tone_preferences') or []
        p.pace_preferences=data.get('pace_preferences') or []
        p.surprise_preferences=data.get('surprise_preferences') or []
        p.popularity_preference=data.get('popularity_preference')
        qp=data.get('quality_preference'); p.quality_preference=None if qp in (None,'any') else qp
        p.confidence=.72
        return p
    except Exception:
        return None
