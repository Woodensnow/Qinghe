"""Local profile drafts: places come from the notes, and timelines fit the packages."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
import ai_draft

NOTES = '我在成都长大，喜欢泡茶馆、吃苍蝇馆子，周末常去人民公园和玉林路。'
FORBIDDEN = ('宽窄巷子', '鹤鸣茶社', '锦里', '春熙路', '杜甫草堂')
HOURS = {'half': 4, 'full': 8, 'evening': 3}


def minutes(value):
    hour, minute = (int(part) for part in value.split(':'))
    return hour * 60 + minute


class LocalDraftTests(unittest.TestCase):
    def test_example_notes_extracts_real_places_and_fits_each_package(self):
        self.assertEqual(ai_draft.extract_places(NOTES), ['人民公园', '玉林路'])
        draft = ai_draft.draft_profile(NOTES, '成都', ['美食探店', '城市漫步'])
        self.assertGreaterEqual(len(draft['bio']), 20)
        self.assertLessEqual(len(draft['bio']), 600)
        self.assertIn('我', draft['bio'])
        seen = set()
        for key, nodes in draft['itineraries'].items():
            self.assertGreaterEqual(len(nodes), 3)
            self.assertLessEqual(len(nodes), 5)
            times = [minutes(node['time']) for node in nodes]
            self.assertEqual(times, sorted(set(times)))
            self.assertLessEqual(times[-1] - times[0], HOURS[key] * 60)
            if key == 'evening':
                self.assertGreaterEqual(times[0], 17 * 60)
            for node in nodes:
                seen.add(node['place'])
                self.assertTrue(node['place'] in NOTES or node['place'] in ai_draft.GENERIC_PLACES)
                for name in FORBIDDEN:
                    self.assertNotIn(name, node['place'])
                    self.assertNotIn(name, node['activity'])
        self.assertTrue({'人民公园', '玉林路'} <= seen)

    def test_highlights_come_from_keywords_and_services(self):
        highlights = ai_draft.draft_profile(NOTES, '成都', ['美食探店', '城市漫步'])['highlights']
        self.assertEqual(highlights, ['带你去泡老茶馆', '按你的口味去探店', '不赶路的城市漫步'])
        self.assertTrue(all(1 <= len(item) <= 20 for item in highlights))
        padded = ai_draft.build_highlights('我想慢慢看看这座城市的日常。', [], 0)
        self.assertEqual(len(padded), 3)
        self.assertEqual(padded, list(ai_draft.FALLBACK_HIGHLIGHTS))

    def test_each_part_can_be_regenerated(self):
        original = ai_draft.draft_profile(NOTES, '成都', ['美食探店', '城市漫步'], variant=0)
        again = ai_draft.draft_profile(NOTES, '成都', ['美食探店', '城市漫步'], variant=1)
        self.assertNotEqual(original['bio'], again['bio'])
        self.assertNotEqual(original['highlights'], again['highlights'])
        self.assertNotEqual(original['itineraries'], again['itineraries'])
        self.assertEqual(set(ai_draft.draft_profile(NOTES, '成都', part='bio')), {'bio'})
        self.assertEqual(set(ai_draft.draft_profile(NOTES, '成都', part='highlights')), {'highlights'})
        self.assertEqual(set(ai_draft.draft_profile(NOTES, '成都', part='itinerary')), {'itineraries'})

    def test_missing_places_stay_generic(self):
        notes = '我喜欢慢慢走路，也喜欢发呆和聊天。'
        self.assertEqual(ai_draft.extract_places(notes), [])
        draft = ai_draft.draft_profile(notes, '成都', ['城市漫步'])
        for nodes in draft['itineraries'].values():
            self.assertTrue(all(node['place'] in ai_draft.GENERIC_PLACES for node in nodes))
            self.assertGreaterEqual(len(nodes), 3)


if __name__ == '__main__':
    unittest.main()
