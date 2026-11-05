"""Exercise the required main.py entry and invalid keyboard input."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import io

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import quote
import main


class CliTests(unittest.TestCase):
    def test_interactive_estimate_and_invalid_number(self):
        guides = [dict(id='g_test', name='测试地陪', city='上海', price=200, headline='城市漫步', packages=[dict(name='半日游', duration='4 小时', price=200)])]
        for keyboard, expected in ((['3', '1', '1', '5', '0'], '预计总价：¥260'), (['3', 'abc', '0'], '请输入整数'), (['2', '上海', '0'], '测试地陪')):
            output = io.StringIO()
            with patch.object(main, 'published_guides', return_value=guides), patch('builtins.input', side_effect=keyboard), patch('sys.stdout', output):
                main.menu()
            self.assertIn(expected, output.getvalue())

    def test_price_boundaries(self):
        for people, expected in ((1, 200), (4, 200), (5, 260), (8, 440)):
            self.assertEqual(quote(200, people), expected)
        for people in (0, 9, 1.5, True):
            with self.assertRaises(ValueError):
                quote(200, people)

    def test_invalid_menu_and_eof(self):
        for keyboard in ('invalid\n0\n', ''):
            result = subprocess.run([sys.executable, str(ROOT / 'main.py')], input=keyboard,
                                    capture_output=True, text=True, encoding='utf-8',
                                    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('已退出' if not keyboard else '请输入 0–4', result.stdout)

    def test_help_and_conflicting_modes(self):
        for args, status in ((['--help'], 0), (['--serve', '--reset'], 2)):
            result = subprocess.run([sys.executable, str(ROOT / 'main.py'), *args], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, status)
