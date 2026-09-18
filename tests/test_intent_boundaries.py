import unittest

from src.filtering import hard_filter
from src.intent_parser import parse_intent
from src.models import Candidate, SceneProfile


def candidate(title, genres, *, emotions=None, risks=None, relationships=None):
    return Candidate(
        content_id=title,
        title=title,
        content_type='movie',
        release_year=2020,
        runtime_minutes=110,
        genres=genres,
        description='',
        scene_tags=['solo'],
        emotion_tags=emotions or [],
        watching_tags=[],
        risk_tags=risks or [],
        cognitive_load='medium',
        platforms=[],
        poster_url=None,
        relationship_tags=relationships or [],
        pace_tags=['moderate'],
    )


class IntentBoundaryTests(unittest.TestCase):
    def test_niche_romance_movie_is_hard_romance(self):
        p=parse_intent('我想看小众恋爱片')
        self.assertIn('Romance',p.required_genres)
        self.assertEqual('niche',p.popularity_preference)
        self.assertIn('movie',p.content_types)

    def test_romance_gate_rejects_pure_puzzle_movie(self):
        p=parse_intent('我想看小众恋爱片')
        romance=candidate('Romance',['Drama','Romance'],relationships=['romantic'])
        puzzle=candidate('Puzzle',['Thriller','Mystery'],emotions=['thought_provoking'])
        kept,dropped=hard_filter([romance,puzzle],p)
        self.assertEqual(['Romance'],[x.title for x in kept])
        self.assertEqual('Puzzle',dropped[0][0].title)

    def test_exploration_does_not_bypass_hard_gate(self):
        p=parse_intent('我想看小众恋爱片，给我点惊喜')
        self.assertEqual('explore',p.exploration_mode)
        puzzle=candidate('Puzzle',['Thriller','Mystery'])
        kept,_=hard_filter([puzzle],p)
        self.assertEqual([],kept)

    def test_no_horror_is_a_hard_negative(self):
        p=parse_intent('想看悬疑，但不要恐怖')
        horror=candidate('Horror',['Thriller','Horror'],risks=['fear_or_horror'])
        thriller=candidate('Thriller',['Thriller'])
        kept,_=hard_filter([horror,thriller],p)
        self.assertEqual(['Thriller'],[x.title for x in kept])

    def test_funny_is_required_signal(self):
        p=parse_intent('和朋友聚会，想看轻松好笑的电影')
        self.assertIn('funny',p.required_signals)
        comedy=candidate('Comedy',['Comedy'],emotions=['funny'])
        drama=candidate('Drama',['Drama'])
        kept,_=hard_filter([comedy,drama],p)
        self.assertEqual(['Comedy'],[x.title for x in kept])


if __name__=='__main__':
    unittest.main()
