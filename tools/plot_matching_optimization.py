"""Optional report plots: pip install matplotlib; no web runtime dependency.

Learning curves of the deployed ensemble, plus v1 / v3 / deployed metrics on
the same synthetic confirmation profiles (each model with its own vocabulary).
"""
import json
from pathlib import Path
import shutil
import statistics
import time

from train_matching import ROOT, DATA_SEED, partition, evaluate
from optimize_matching import load

MODELS = ROOT / 'server' / 'models'
FONTS = ('PingFang SC', 'Hiragino Sans GB', 'Heiti SC', 'Microsoft YaHei', 'Arial Unicode MS')


def chinese_font(plt):
    from matplotlib import font_manager
    windows = Path('C:/Windows/Fonts/msyh.ttc')
    if windows.exists():
        font_manager.fontManager.addfont(str(windows))
    available = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family'] = [name for name in FONTS if name in available] or ['sans-serif']
    plt.rcParams['axes.unicode_minus'] = False


def load_ensemble(path):
    import matching_service
    original, cached = matching_service.MODEL_PATH, matching_service._engine
    matching_service.MODEL_PATH, matching_service._engine = path, None
    try:
        return matching_service.load_engine()
    finally:
        matching_service.MODEL_PATH, matching_service._engine = original, cached


def timing(module, dataset):
    import torch
    pairs = dataset['pairs'][dataset['eligible']]
    module.eval()
    with torch.inference_mode():
        for _ in range(5):
            module(dataset['features'], pairs)
        samples = []
        for _ in range(20):
            start = time.perf_counter()
            module(dataset['features'], pairs)
            samples.append(1000 * (time.perf_counter() - start))
    return dict(medianMs=statistics.median(samples), maxMs=max(samples), iterations=20), len(pairs)


def main():
    import torch
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    chinese_font(plt)
    torch.set_num_threads(2)
    current, vocab, metadata = load_ensemble(MODELS / 'matching.pt')
    version = metadata['model'].split('-')[2]
    report = json.loads((ROOT / metadata['optimizationReport']).read_text(encoding='utf-8'))
    runs = ROOT / 'output' / ('matching_refinement_' + version)
    previous, v1 = load(MODELS / 'matching_v1.pt')
    v3, v3_vocab, _ = load_ensemble(MODELS / 'matching_v3.pt')
    rows, timings = [], {}
    for label, module, vocabulary, color in [('v1', v1, previous['vocab'], '#b9c4bd'),
                                             ('v3', v3, v3_vocab, '#7fa58f'),
                                             (version, current, vocab, '#24734d')]:
        dataset = partition('confirmation', DATA_SEED, 64, 48, vocab=vocabulary)
        rows.append((label, evaluate(module, dataset), color))
        timings[label], scored = timing(module, dataset)
    timing_report = dict(torchVersion=str(torch.__version__), threads=2, graphTravelers=64, graphGuides=48,
                         scoredPairs=scored, scope='warm in-process CPU forward only; excludes graph construction, loading and HTTP',
                         results=timings)
    (ROOT / 'docs' / 'matching_inference_timing.json').write_text(json.dumps(timing_report, indent=2), encoding='utf-8')

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5), gridspec_kw={'width_ratios': [1.35, 1, 1]})
    for color, seed in zip(('#24734d', '#2876a6', '#a56528'), (42, 7, 101)):
        run = json.loads((runs / f'{report["selectedPreset"]}_{seed}.json').read_text(encoding='utf-8'))
        history = run['history']
        epochs = [row['epoch'] for row in history]
        axes[0].plot(epochs, [row['trainEligibleMSE'] for row in history], color=color, alpha=.55, linewidth=1)
        axes[0].plot(epochs, [row['validationEligibleMSE'] for row in history], color=color, linestyle='--',
                     linewidth=1.7, label=f'种子 {seed}，最佳第 {run["bestEpoch"]} 轮')
        best = history[run['bestEpoch'] - 1]
        axes[0].scatter([best['epoch']], [best['validationEligibleMSE']], color=color, s=26, zorder=4)
    axes[0].set(title=f'{version} 学习曲线（{report["selectedPreset"]}，{metadata.get("trainingDevice", "cpu").upper()} 训练）',
                xlabel='训练轮次', ylabel='合格候选 MSE（对数刻度）')
    axes[0].set_yscale('log')
    axes[0].legend(fontsize=8.5, frameon=False)
    axes[0].text(.02, .03, '实线：训练集　虚线：验证集\n圆点：保存的最佳权重', transform=axes[0].transAxes, fontsize=8.5)
    width = .8 / len(rows)
    for index, (label, metrics, color) in enumerate(rows):
        offset = (index - (len(rows) - 1) / 2) * width
        values = [100 * metrics['eligibleMAE'][key] for key in ('traveler', 'guide')]
        bars = axes[1].bar([offset, 1 + offset], values, width * .92, label=label, color=color)
        axes[1].bar_label(bars, fmt='%.1f', padding=3, fontsize=8.5)
        ranks = [metrics['ndcg5'][key] for key in ('mutualTraveler', 'mutualGuide')]
        bars = axes[2].bar([offset, 1 + offset], ranks, width * .92, label=label, color=color)
        axes[2].bar_label(bars, fmt='%.3f', padding=3, fontsize=8)
    axes[1].set(title='确认集评分误差（越低越好）', ylabel='合格候选 MAE × 100', xticks=[0, 1],
                xticklabels=['旅人方向', '地陪方向'], ylim=(0, 24))
    axes[1].legend(fontsize=9, frameon=False)
    axes[2].set(title='确认集双方排序（越高越好）', ylabel='NDCG@5', xticks=[0, 1],
                xticklabels=['推荐给旅人', '推荐给地陪'], ylim=(0, 1.12))
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.18)
        ax.set_axisbelow(True)
    eligible = rows[-1][1]['eligiblePairs']
    fig.suptitle(f'{version} 训练损失与确认集对比（确认集：64 位新旅人、48 位新地陪、{eligible} 个合格候选对）', fontsize=14, weight='bold')
    fig.text(.5, .02, '三个模型在同一批确认资料上评估，各自使用自己的词表；配置只按验证集选择。'
             '指标衡量对合成规则的拟合，不代表真实用户接受率。', ha='center', fontsize=9)
    fig.tight_layout(rect=[0, .06, 1, .93])
    path = ROOT / 'docs' / 'matching_optimization.png'
    fig.savefig(path, dpi=180)
    plt.close(fig)
    copy = ROOT / '训练图表' / '优化前后对照.png'
    copy.parent.mkdir(exist_ok=True)
    shutil.copyfile(path, copy)
    print(json.dumps(timing_report, indent=2))
    print(path)
    print(copy)


if __name__ == '__main__':
    main()
