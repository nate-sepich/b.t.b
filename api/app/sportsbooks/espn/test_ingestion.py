import unittest
from datetime import datetime

from ingestion import IngestionProvider

class TestIngestionProvider(unittest.TestCase):

    def setUp(self):
        self.provider = IngestionProvider()

    def test_parse_copy_paste_data(self):
        raw_text = """Straight
        Win · $112.22
        Over 23.5
        1st Half Total Points
        -120
        Final · NCAAF
        BAL Ravens-logo
        BAL Ravens
        28
        DAL Cowboys-logo
        DAL Cowboys
        25
        Sep 22, 2024 at 3:25 PM
        $61.21
        Bet
        $112.22
        Payout
        Settled: Sep 22, 2024 at 4:50 PM
        ID: ZuD9zrKPttNN8kLtpsoAI3xl8Ac="""
        
        expected_output = [{
            "bet_id": "ZuD9zrKPttNN8kLtpsoAI3xl8Ac=",
            "bet_type": "Straight",
            "outcome": "Win",
            "winnings": 112.22,
            "bet_description": "Over 23.5",
            "bet_details": "1st Half Total Points",
            "odds": -120,
            "league": "NCAAF",
            "away_team": "BAL Ravens",
            "away_score": 28,
            "home_team": "DAL Cowboys",
            "home_score": 25,
            "bet_datetime": "2024-09-22 15:25:00",
            "bet": 61.21,
            "payout": 112.22,
            "settled_date": "Sep 22, 2024 at 4:50 PM"
        }]

        self.assertEqual(self.provider.parse_copy_paste_data(raw_text), expected_output)

if __name__ == '__main__':
    unittest.main()
