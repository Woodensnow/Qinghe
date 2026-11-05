"""Check clean submission contents and a CLI run after fresh extraction."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_submission_excludes_private_data_and_runs(self):
        scratch = ROOT / 'tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            project = Path(directory) / 'project'
            project.mkdir()
            for name in ('main.py', 'start.py', 'start.ps1', 'start.bat', 'start.sh', 'stop.sh', 'README.md', 'CREDITS.md', 'pyproject.toml', 'requirements-matching.txt', '.gitignore'):
                shutil.copy2(ROOT / name, project)
            for folder in ('server', 'tests', 'docs', 'tools', '.github'):
                shutil.copytree(ROOT / folder, project / folder, ignore=shutil.ignore_patterns('data.json', '*.tmp', '*.pid', '__pycache__'))
            (project / 'server' / 'data.json').write_text('{"private": true}')
            uploads = project / 'public' / 'uploads'
            uploads.mkdir(parents=True)
            (uploads / 'private.jpg').write_bytes(b'private')
            (project / 'public' / 'index.html').write_text('<h1>Qinghe</h1>')
            result = subprocess.run([sys.executable, str(project / 'tools' / 'package_project.py'), '--group', '999'], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            extracted = Path(directory) / 'extracted'
            with ZipFile(project / 'output' / 'group999_project.zip') as bundle:
                names = set(bundle.namelist())
                for required in ('main.py', 'README.md', 'server/seed-data.json', 'server/catalog.json', 'tests/test_server.py'):
                    self.assertIn(required, names)
                self.assertNotIn('server/data.json', names)
                self.assertNotIn('public/uploads/private.jpg', names)
                bundle.extractall(extracted)
            result = subprocess.run([sys.executable, str(extracted / 'main.py')], input='2\n上海\n0\n', capture_output=True, text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('林小满', result.stdout)
            self.assertTrue((extracted / 'server' / 'data.json').exists())
