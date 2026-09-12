"""Questionnaire-history scoring tests; no AI, Whisper, or SER dependencies."""
import unittest
from types import SimpleNamespace

from app.cases import calculate_distress_score, historical_distress


QUESTIONNAIRE = SimpleNamespace(
    mood=2, anxiety=3, sleep=1, hopelessness=2,
    social_withdrawal=2, self_harm_thoughts=2,
)


class HistoricalDistressTests(unittest.TestCase):
    def test_weights_trend_bonus_and_bound(self):
        # Newest first: weighted history = (90*.4 + 70*.3 + 50*.2 + 30*.1) / 1.
        history = [
            {'score': 90, 'created_at': '2026-09-12T00:00:00+00:00'},
            {'score': 70, 'created_at': '2026-09-11T00:00:00+00:00'},
            {'score': 50, 'created_at': '2026-09-10T00:00:00+00:00'},
            {'score': 30, 'created_at': '2026-09-09T00:00:00+00:00'},
        ]
        details = historical_distress(history)
        self.assertEqual(details, {'score': 70.0, 'trend': 'rising', 'delta': 60})
        score, risk, metadata = calculate_distress_score(QUESTIONNAIRE, history)
        # Questionnaire=50: 50*.8 + 70*.2 + 5 rising bonus = 59.
        self.assertEqual((score, risk), (59, 'High'))
        self.assertEqual(metadata['escalationBonus'], 5)

    def test_first_checkin_keeps_questionnaire_result(self):
        score, risk, metadata = calculate_distress_score(QUESTIONNAIRE, [])
        self.assertEqual((score, risk), (50, 'High'))
        self.assertIsNone(metadata['historicalScore'])
        self.assertEqual(metadata['recentTrend'], 'stable')

