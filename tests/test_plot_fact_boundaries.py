from __future__ import annotations

import unittest

from src.intent_parser import parse_intent
from src.filtering import hard_filter
from src.models import Candidate


def candidate(title: str, *, facts: dict[str,bool] | None = None, risks: list[str] | None = None) -> Candidate:
    return Candidate(
        content_id=title,
        title=title,
        content_type='movie',
        release_year=2024,
        runtime_minutes=105,
        genres=['Comedy'],
        description='demo',
        scene_tags=['solo','family'],
        emotion_tags=['funny','light','relaxing'],
        watching_tags=[],
        risk_tags=risks or [],
        cognitive_load='low',
        platforms=[],
        poster_url='data:image/svg+xml,poster',
        relationship_tags=['friendship'],
        tone_tags=['warm','playful'],
        content_facts=facts or {},
        understanding_confidence=.8,
    )


class PlotFactBoundaryTests(unittest.TestCase):
    def test_no_death_compiles_to_positive_fact(self):
        p=parse_intent('我想看没有任何人死去的电影')
        self.assertIn('no_character_death', p.required_facts)
        self.assertIn('movie', p.content_types)

    def test_unknown_does_not_equal_safe(self):
        p=parse_intent('我想看没有任何人死去的电影')
        safe=candidate('safe',facts={'no_character_death':True})
        unknown=candidate('unknown',facts={})
        kept,dropped=hard_filter([safe,unknown],p)
        self.assertEqual([x.title for x in kept],['safe'])
        self.assertTrue(any('required_fact_missing:no_character_death' in reason for _,reasons in dropped for reason in reasons))

    def test_multiple_plot_facts_are_all_required(self):
        p=parse_intent('没人死，而且结局圆满，不要血腥')
        self.assertIn('no_character_death',p.required_facts)
        self.assertIn('happy_ending',p.required_facts)
        self.assertIn('no_gore',p.required_facts)
        good=candidate('good',facts={'no_character_death':True,'happy_ending':True,'no_gore':True})
        missing=candidate('missing',facts={'no_character_death':True,'no_gore':True})
        kept,_=hard_filter([good,missing],p)
        self.assertEqual([x.title for x in kept],['good'])

    def test_explicit_year_is_compiled(self):
        p=parse_intent('想看2026国产剧')
        self.assertEqual(p.year_min,2026)
        self.assertIn('series',p.content_types)
        self.assertEqual(p.language,'Chinese')


if __name__=='__main__':
    unittest.main()
