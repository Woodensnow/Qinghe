"""INT6181 entry point: a Python CLI with an optional browser interface."""
import argparse
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'server'))
from pricing import quote


def published_guides(city=''):
    """Return available guides, optionally filtered by city, cheapest first."""
    from store import data
    return sorted((g for g in data()['guides'] if g['status'] == 'published' and
                   (not city or g['city'] == city)), key=lambda g: g['price'])


def reset_demo():
    from server import PID_FILE
    from store import reset, DATA_FILE
    if PID_FILE.exists():
        raise ValueError('请先关闭服务，再重置。若服务已退出，请确认后移除 server/server.pid。')
    reset()
    uploads = ROOT / 'public' / 'uploads'
    if uploads.exists():
        for entry in uploads.iterdir():
            if entry.is_file() and not entry.is_symlink() and entry.name != '.gitkeep':
                entry.unlink()
    print(f'演示数据已重置：{DATA_FILE}')


def browse():
    city = input('城市（回车查看全部）：').strip()
    guides = published_guides(city)
    if not guides:
        print('该城市暂无接单服务，请尝试其他城市。')
    for guide in guides:
        print(f'{guide["id"]} | {guide["name"]} | {guide["city"]} | ¥{guide["price"]} 起 | {guide["headline"]}')


def estimate():
    guides = published_guides()
    for index, guide in enumerate(guides, 1):
        print(f'{index}. {guide["name"]}（{guide["city"]}）')
    if not guides:
        print('暂无接单服务。')
        return
    index = read_integer('选择地陪序号：')
    if not 1 <= index <= len(guides):
        raise ValueError('请选择有效的地陪序号')
    packages = guides[index - 1]['packages']
    for index, package in enumerate(packages, 1):
        print(f'{index}. {package["name"]} / {package["duration"]} / ¥{package["price"]}')
    index = read_integer('选择套餐序号：')
    if not 1 <= index <= len(packages):
        raise ValueError('请选择有效的套餐序号')
    people = read_integer('同行人数（1–8）：')
    total = quote(packages[index - 1]['price'], people)
    print(f'预计总价：¥{total}（超过 4 人，每人加 ¥60）。本次仅估价，不创建预约。')


def read_integer(prompt):
    try:
        return int(input(prompt))
    except ValueError:
        raise ValueError('请输入整数，例如 1、2 或 3') from None


def serve():
    runpy.run_path(str(ROOT / 'server' / 'server.py'), run_name='__main__')


def menu():
    print('青禾 · 城市轻兼职 / INT6181 Python 项目')
    while True:
        print('\n1. 启动网页服务\n2. 查询地陪\n3. 计算套餐报价\n4. 运行测试\n0. 退出')
        try:
            choice = input('请选择：').strip()
            if choice == '0':
                return
            if choice == '1':
                serve()
                return
            elif choice == '2':
                browse()
            elif choice == '3':
                estimate()
            elif choice == '4':
                result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT)
                print('测试通过。' if result.returncode == 0 else '测试未通过，请查看上方错误信息。')
            else:
                print('请输入 0–4 之间的选项。')
        except (ValueError, OSError) as error:
            print(f'操作未完成：{error}')
        except (EOFError, KeyboardInterrupt):
            print('\n已退出。')
            return


def main():
    parser = argparse.ArgumentParser(description='青禾 · INT6181 Python 应用；不带参数进入命令行菜单')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--serve', action='store_true', help='直接启动网页服务')
    mode.add_argument('--reset', action='store_true', help='清空业务数据与上传图片，恢复演示数据（先关闭服务）')
    args = parser.parse_args()
    try:
        if args.reset:
            reset_demo()
        elif args.serve:
            serve()
        else:
            menu()
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
    except KeyboardInterrupt:
        print('\n已退出。')


if __name__ == '__main__':
    main()
