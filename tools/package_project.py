"""Create a clean course source submission, excluding live private data."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='打包 INT6181 源码、初始数据、测试和文档')
    parser.add_argument('--group', type=int, required=True, help='实际小组编号，例如 3')
    args = parser.parse_args()
    if args.group < 1:
        parser.error('组号必须为正整数')
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    archive = output / f'group{args.group}_project.zip'
    included = []
    folders = ('server', 'public', 'tests', 'docs', 'tools', 'preview', '.github')
    excluded_parts = {'__pycache__', '.venv', '.git', 'uploads'}
    for folder in folders:
        for path in (ROOT / folder).rglob('*'):
            relative = path.relative_to(ROOT)
            if path.is_file() and not path.is_symlink() and not excluded_parts.intersection(relative.parts) and path.name not in {'data.json', 'data.json.tmp', 'server.pid'} and not path.name.endswith('.local.json') and not path.name.startswith('.env') and path.suffix not in {'.pyc', '.pyo', '.log'}:
                included.append(path)
    included += [ROOT / name for name in ('main.py', 'start.py', 'start.ps1', 'start.bat', 'start.sh', 'stop.sh', 'README.md', 'CREDITS.md', 'pyproject.toml', 'requirements-matching.txt', '.gitignore')]
    with ZipFile(archive, 'w', ZIP_DEFLATED) as bundle:
        for path in sorted(included):
            bundle.write(path, path.relative_to(ROOT).as_posix())
    print(f'已生成：{archive}\n包含源码、测试、演示初始数据和文档；不包含现有账号、聊天和上传图片。')


if __name__ == '__main__':
    main()
