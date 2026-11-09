"""Frontend draft checks live in a DOM-free module so Node can run them."""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ItineraryClientTests(unittest.TestCase):
    def node(self, body):
        script = (
            "import { readPackageItinerary, validateItineraries, validateHighlights, "
            "draftFailureMessage, notesProblem } from './public/js/itinerary.js';\n"
            + body
            + "\nprocess.stdout.write(JSON.stringify(result));\n"
        )
        completed = subprocess.run(
            ['node', '--input-type=module', '-e', script],
            cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_publish_itineraries_require_every_package(self):
        node = [
            dict(time='10:00', place='人民公园', activity='喝茶'),
            dict(time='11:00', place='玉林路', activity='吃饭'),
            dict(time='12:00', place='沿途散步', activity='慢慢走'),
        ]
        evening = [
            dict(time='17:00', place='人民公园', activity='喝茶'),
            dict(time='18:00', place='玉林路', activity='吃饭'),
            dict(time='19:00', place='沿途散步', activity='慢慢走'),
        ]
        result = self.node(
            "const node = " + json.dumps(node) + ";\n"
            "const evening = " + json.dumps(evening) + ";\n"
            "const full = { half: node, full: node, evening };\n"
            "const result = {\n"
            "  ok: validateItineraries(full).ok,\n"
            "  keys: Object.keys(validateItineraries(full).itineraries),\n"
            "  missing: validateItineraries({ half: node, full: node }).message,\n"
            "  blank: validateItineraries({ half: [{ time: '', place: '', activity: '' }], full: node, evening }).ok,\n"
            "  early: validateItineraries({ half: node, full: node, evening: node }).message,\n"
            "  highlights: validateHighlights(['  带你去泡茶  ', '按你的口味去探店', '不赶路的城市漫步']),\n"
            "  emptyHighlights: validateHighlights(['', '  ', '']).omit,\n"
            "  rate: draftFailureMessage({ status: 429, message: '生成太频繁，请稍后再试' }),\n"
            "  bad: draftFailureMessage({ status: 400, message: '请写 6 到 300 字，方便生成简介和行程' }),\n"
            "  offline: draftFailureMessage({ status: 0, message: 'ignored' }),\n"
            "  notes: notesProblem('太短'),\n"
            "  bare: readPackageItinerary({ key: 'half' }),\n"
            "  weird: readPackageItinerary({ key: 'evening', itinerary: 'nope' }),\n"
            "  place: readPackageItinerary({ itinerary: [{ time: '18:00', place: '<b>茶馆</b>', activity: '坐下' }] })[0].place,\n"
            "};\n"
        )
        self.assertTrue(result['ok'])
        self.assertEqual(result['keys'], ['half', 'full', 'evening'])
        self.assertIn('傍晚轻陪游', result['missing'])
        self.assertFalse(result['blank'])
        self.assertIn('17:00', result['early'])
        self.assertEqual(result['highlights']['highlights'][0], '带你去泡茶')
        self.assertTrue(result['emptyHighlights'])
        self.assertEqual(result['rate'], '生成太频繁，请稍后再试')
        self.assertEqual(result['bad'], '请写 6 到 300 字，方便生成简介和行程')
        self.assertEqual(result['offline'], '网络好像开小差了，请稍后再试')
        self.assertIn('6 到 300', result['notes'])
        self.assertEqual(result['bare'], [])
        self.assertEqual(result['weird'], [])
        self.assertEqual(result['place'], '<b>茶馆</b>')

    def test_detail_page_does_not_index_itinerary_by_key(self):
        detail = (ROOT / 'public/js/pages/detail.js').read_text(encoding='utf-8')
        timeline = (ROOT / 'public/js/components/itinerary-timeline.js').read_text(encoding='utf-8')
        draft = (ROOT / 'public/js/components/ai-draft.js').read_text(encoding='utf-8')
        become = (ROOT / 'public/js/pages/become.js').read_text(encoding='utf-8')
        self.assertNotIn('itineraries[', detail)
        self.assertIn('readPackageItinerary', detail)
        self.assertIn('textContent', timeline)
        self.assertNotIn('innerHTML', timeline.replace("button.innerHTML = `${icon('clock')}<span></span>${icon('chevron-down')}`;", ''))
        self.assertIn('itineraries: routes.itineraries', become)
        self.assertIn('AI 帮我写', become)
        for needle in ('${draft.', '${result.', '${node.', '${place}', '${activity}'):
            self.assertNotIn(needle, draft)
