"""Plot recorded 500-epoch one/two-layer losses, without retraining."""
import json

from train_matching import ROOT


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    # Use the system Chinese font when present; Matplotlib otherwise follows
    # its configured font family for the existing Chinese report workflow.
    from pathlib import Path
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['svg.fonttype'] = 'none'
    figure, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, layout='constrained')
    for column, seed in enumerate((42, 7, 101)):
        for depth, folder, color in [(1, 'matching_500', '#28744e'), (2, 'matching_500_encoder2', '#bd6927')]:
            report = json.loads((ROOT / 'output' / folder / f'member_{seed}.json').read_text(encoding='utf-8'))
            history = report['history']
            assert len(history) == 500
            epochs = [row['epoch'] for row in history]
            axes[0, column].plot(epochs, [row['trainEligibleMSE'] for row in history], color=color, label=f'{depth} 层 Encoder', linewidth=1.3)
            axes[1, column].plot(epochs, [row['validationEligibleMSE'] for row in history], color=color, label=f'{depth} 层，最佳轮次 {report["bestEpoch"]}', linewidth=1.3)
            best = report['bestEpoch']
            axes[1, column].scatter(best, history[best - 1]['validationEligibleMSE'], color=color, s=28, zorder=4)
        axes[0, column].set_title(f'随机种子 {seed}', fontsize=14)
        for row in (0, 1):
            axes[row, column].set_yscale('log')
            axes[row, column].set_xlim(0, 500)
            axes[row, column].grid(axis='y', alpha=.2)
            axes[row, column].legend(frameon=False, fontsize=9)
        axes[1, column].set_xlabel('实际训练轮次')
    axes[0, 0].set_ylabel('训练 MSE（合格候选，对数刻度）')
    axes[1, 0].set_ylabel('验证 MSE（合格候选，对数刻度）')
    figure.suptitle('一层与两层 Encoder 对照 · 三个种子各训练满 500 轮', fontsize=18)
    output = ROOT / '训练图表'
    output.mkdir(exist_ok=True)
    for extension in ('png', 'svg'):
        figure.savefig(output / f'Encoder一层与两层_500轮损失对照.{extension}', dpi=180)
    plt.close(figure)
    print(output / 'Encoder一层与两层_500轮损失对照.png')


if __name__ == '__main__':
    main()
