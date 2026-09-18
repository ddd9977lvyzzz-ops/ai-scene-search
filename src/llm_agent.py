from __future__ import annotations

"""Server-side LLM brain for YING.

The LLM does semantic interpretation and response planning. Deterministic code remains authoritative
for hard constraints and catalog truth. This prevents the model from "chatting around" platform,
runtime, or trigger constraints.

OpenAI Responses API is used so the agent can later add web/file/function tools without changing
the product contract. Secrets stay server-side; GitHub Pages never receives the API key.
"""

import json
import os
from dataclasses import asdict
from typing import Any

from .models import SceneProfile


PLAN_SCHEMA = {
    "type":"object",
    "properties":{
        "query_rewrite":{"type":"string"},
        "companions":{"anyOf":[{"type":"string","enum":["solo","family","friends","couple"]},{"type":"null"}]},
        "scene":{"anyOf":[{"type":"string","enum":["party","late_night","commute","weekend","meal"]},{"type":"null"}]},
        "moods":{"type":"array","items":{"type":"string","enum":["light","relaxing","healing","funny","exciting","tense","thought_provoking","scary","romantic"]}},
        "cognitive_load":{"anyOf":[{"type":"string","enum":["low","medium","high"]},{"type":"null"}]},
        "relationship_focus":{"type":"array","items":{"type":"string","enum":["romantic","family","friendship","workplace"]}},
        "tone_preferences":{"type":"array","items":{"type":"string","enum":["sweet","gentle","realistic","bittersweet","dark","playful","warm","quirky","stylized"]}},
        "pace_preferences":{"type":"array","items":{"type":"string","enum":["slow","moderate","fast"]}},
        "surprise_preferences":{"type":"array","items":{"type":"string","enum":["plot_reveal","worldbuilding","relationship_turns","comic_payoff","visual_set_piece","insight","fresh_premise"]}},
        "popularity_preference":{"anyOf":[{"type":"string","enum":["niche","mainstream"]},{"type":"null"}]},
        "decision_style":{"type":"string","enum":["list","pick_one"]},
        "needs_clarification":{"type":"boolean"},
        "clarification_question":{"anyOf":[{"type":"string"},{"type":"null"}]},
        "retrieval_hints":{"type":"array","items":{"type":"string"}},
        "reasoning_note":{"type":"string"}
    },
    "required":[
        "query_rewrite","companions","scene","moods","cognitive_load","relationship_focus",
        "tone_preferences","pace_preferences","surprise_preferences","popularity_preference",
        "decision_style","needs_clarification","clarification_question","retrieval_hints","reasoning_note"
    ],
    "additionalProperties":False
}

ANSWER_SCHEMA = {
    "type":"object",
    "properties":{
        "assistant_message":{"type":"string"},
        "decision_summary":{"type":"string"},
        "follow_up_suggestions":{"type":"array","items":{"type":"string"}}
    },
    "required":["assistant_message","decision_summary","follow_up_suggestions"],
    "additionalProperties":False
}


class LLMAgentBrain:
    def __init__(self):
        self.api_key=os.getenv("OPENAI_API_KEY","").strip()
        self.model=os.getenv("OPENAI_AGENT_MODEL","gpt-6-astra").strip()
        self.base_url=os.getenv("OPENAI_BASE_URL","").strip() or None
        self.enabled_flag=os.getenv("OPENAI_AGENT_ENABLED","1").strip().lower() in {"1","true","yes"}
        self.required=os.getenv("OPENAI_AGENT_REQUIRED","0").strip().lower() in {"1","true","yes"}
        self._client=None

    @property
    def enabled(self) -> bool:
        return self.enabled_flag and bool(self.api_key)

    @property
    def mode(self) -> str:
        if self.enabled:
            return f"openai-responses:{self.model}"
        return "deterministic-fallback"

    def _client_or_raise(self):
        if not self.enabled:
            if self.required:
                raise RuntimeError("OPENAI_AGENT_REQUIRED=1 but OPENAI_API_KEY is missing")
            return None
        if self._client is None:
            from openai import OpenAI
            self._client=OpenAI(api_key=self.api_key,base_url=self.base_url)
        return self._client

    def plan(self, text: str, current_profile: SceneProfile) -> dict[str,Any] | None:
        client=self._client_or_raise()
        if client is None:
            return None
        try:
            resp=client.responses.create(
                model=self.model,
                reasoning={"effort":"low"},
                instructions=(
                    "You are the semantic planning layer of YING, a scene-aware film/TV decision agent. "
                    "The deterministic system separately extracts HARD constraints such as platform, runtime, "
                    "year, explicit forbidden content and plot facts. Never relax, negate, or overwrite those. "
                    "Your job is to understand implicit scene, emotional intent, cognitive load, tone, pace, "
                    "relationship focus and how decisive the user wants the agent to be. "
                    "Return concise structured JSON. Ask a clarification only when the request is genuinely "
                    "underspecified enough that retrieval would be arbitrary."
                ),
                input=json.dumps({
                    "user_text":text,
                    "current_profile":current_profile.to_dict(),
                },ensure_ascii=False),
                text={"format":{"type":"json_schema","name":"ying_query_plan","strict":True,"schema":PLAN_SCHEMA}},
            )
            return json.loads(resp.output_text)
        except Exception:
            if self.required:
                raise
            return None

    @staticmethod
    def soft_patch(plan: dict[str,Any] | None) -> SceneProfile | None:
        if not plan:
            return None
        p=SceneProfile()
        p.companions=plan.get("companions")
        p.scene=plan.get("scene")
        p.moods=plan.get("moods") or []
        p.cognitive_load=plan.get("cognitive_load")
        p.relationship_focus=plan.get("relationship_focus") or []
        p.tone_preferences=plan.get("tone_preferences") or []
        p.pace_preferences=plan.get("pace_preferences") or []
        p.surprise_preferences=plan.get("surprise_preferences") or []
        p.popularity_preference=plan.get("popularity_preference")
        p.confidence=.82
        return p

    def compose(
        self,
        *,
        user_text: str,
        profile: SceneProfile,
        results: list[dict[str,Any]],
        social_policy: dict[str,Any] | None = None,
    ) -> dict[str,Any] | None:
        client=self._client_or_raise()
        if client is None:
            return None
        grounded=[]
        for item in results[:5]:
            grounded.append({
                "title":item.get("title"),
                "year":item.get("release_year"),
                "type":item.get("content_type"),
                "runtime":item.get("runtime_minutes"),
                "platforms":item.get("platforms") or [],
                "genres":item.get("genres") or [],
                "why":item.get("why"),
                "watchouts":item.get("watchouts") or [],
                "surprises":item.get("surprises") or [],
                "caution":item.get("caution"),
                "score":item.get("score"),
                "evidence":item.get("evidence") or {},
            })
        try:
            resp=client.responses.create(
                model=self.model,
                reasoning={"effort":"low"},
                instructions=(
                    "You are YING, a concise film/TV decision agent. Use ONLY the supplied candidate and "
                    "evidence data. Do not invent titles, platform availability, plot facts, reviews, ratings "
                    "or social-media claims. Explain the decision in natural Chinese, not as a database dump. "
                    "Prioritize the user's current scene and explicit constraints. If evidence is uncertain, "
                    "say so. Keep the main assistant_message under 220 Chinese characters unless the user asked "
                    "for detail."
                ),
                input=json.dumps({
                    "user_text":user_text,
                    "profile":profile.to_dict(),
                    "candidates":grounded,
                    "social_policy":social_policy or {},
                },ensure_ascii=False),
                text={"format":{"type":"json_schema","name":"ying_grounded_answer","strict":True,"schema":ANSWER_SCHEMA}},
            )
            return json.loads(resp.output_text)
        except Exception:
            if self.required:
                raise
            return None
