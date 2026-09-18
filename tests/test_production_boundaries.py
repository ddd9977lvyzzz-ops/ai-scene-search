from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.models import SceneProfile
from src.llm_agent import LLMAgentBrain
from scripts.backfill_real_posters import valid_real_url


class ProductionBoundaryTests(unittest.TestCase):
    def test_new_platform_replaces_old_platform(self):
        p=SceneProfile(platforms=['iqiyi'])
        p.merge(SceneProfile(platforms=['netflix']))
        self.assertEqual(p.platforms,['netflix'])

    def test_no_api_key_is_explicit_fallback_not_fake_llm(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'','OPENAI_AGENT_ENABLED':'1','OPENAI_AGENT_REQUIRED':'0'},clear=False):
            brain=LLMAgentBrain()
            self.assertFalse(brain.enabled)
            self.assertEqual(brain.mode,'deterministic-fallback')
            self.assertIsNone(brain.plan('想看轻松一点的电影',SceneProfile()))

    def test_real_poster_gate_rejects_data_uri(self):
        self.assertTrue(valid_real_url('https://image.tmdb.org/t/p/w500/a.jpg'))
        self.assertTrue(valid_real_url('http://static.tvmaze.com/a.jpg'))
        self.assertFalse(valid_real_url('data:image/svg+xml,<svg/>'))
        self.assertFalse(valid_real_url(''))


if __name__=='__main__':
    unittest.main()
