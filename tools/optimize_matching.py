"""Validation-only configuration selection; one final test and promotion gate."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean, pstdev
import sys

from train_matching import ROOT, DATA_SEED, PRESETS, partition, train, evaluate


def load(path):
    import torch
    from matching_model import TinyBilateralMatcher
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    model = TinyBilateralMatcher(len(checkpoint['vocab']) + 2, **checkpoint.get('config', {}))
    model.load_state_dict(checkpoint['weights'])
    return checkpoint, model


def run(output, epochs=120):
    import torch
    from matching_evaluation import score_metrics
    from matching_data import synthetic_profiles
    torch.set_num_threads(2)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    runs = []

    def experiment(preset, seed):
        path = output / f'{preset}_{seed}.pt'
        report = train(path, epochs=epochs, seed=seed, preset=preset, patience=15)
        record = dict(preset=preset, seed=seed, path=str(path), validation=report['validationMetrics'],
                      parameters=report['parameters'], bestEpoch=report['bestEpoch'], stoppedEpoch=report['epochs'])
        runs.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return record

    # Freeze all configurations and data partitions before any test evaluation.
    for preset in ('reference', 'compact', 'regularized', 'lower_lr', 'rank_aware'):
        experiment(preset, 42)
    finalists = [r['preset'] for r in sorted(runs, key=lambda r: r['validation']['mse'])[:2]]
    for preset in finalists:
        for seed in (7, 101):
            experiment(preset, seed)
    aggregates = {preset: mean(r['validation']['mse'] for r in runs if r['preset'] == preset) for preset in finalists}
    selected_preset = min(aggregates, key=aggregates.get)
    selected_runs = [r for r in runs if r['preset'] == selected_preset]
    deployed = min(selected_runs, key=lambda r: r['validation']['mse'])
    # Selection is now final. Test is not used to choose configurations or seed.
    test_results = []
    for record in selected_runs:
        checkpoint, model = load(record['path'])
        test = partition('test', DATA_SEED, travelers=48, guides=36, vocab=checkpoint['vocab'])
        test_results.append(dict(seed=record['seed'], metrics=evaluate(model, test)))
    selected_test = next(r['metrics'] for r in test_results if r['seed'] == deployed['seed'])
    original_path = ROOT / 'server' / 'models' / 'matching_v1.pt'
    old_checkpoint, old_model = load(original_path)
    old_test = partition('test', DATA_SEED, travelers=48, guides=36, vocab=old_checkpoint['vocab'])
    original_test = evaluate(old_model, old_test)
    training = partition('train', DATA_SEED, travelers=96, guides=72)
    teacher = old_test['targets'].tolist()
    baseline = score_metrics([training['targets'].mean(0).tolist()] * len(teacher), teacher, old_test['trips'], old_test['guides'])
    oracle = score_metrics(teacher, teacher, old_test['trips'], old_test['guides'])
    promoted = (all(selected_test['mae'][key] < original_test['mae'][key] for key in ('traveler', 'guide')) and
                all(selected_test['ndcg5'][key] >= original_test['ndcg5'][key] for key in ('mutualTraveler', 'mutualGuide')))
    manifest = {}
    for split, n, m, offset in [('train', 96, 72, 0), ('validation', 32, 24, 1000), ('test', 48, 36, 2000)]:
        items = synthetic_profiles(DATA_SEED + offset, n, m, split=split)
        manifest[split] = dict(travelers=n, guides=m, pairs=n*m,
                               sha256=hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
    spread = {key: dict(mean=mean(r['metrics']['mae'][key] for r in test_results),
                       std=pstdev(r['metrics']['mae'][key] for r in test_results)) for key in ('traveler', 'guide')}
    summary = dict(protocol='v2: actor/template-held-out; selection by validation MSE only; test after selection',
                   dataSeed=DATA_SEED, splits=manifest, runs=runs, finalistValidationMeanMSE=aggregates,
                   selectedPreset=selected_preset, selectedSeed=deployed['seed'], selectedTest=selected_test,
                   originalV1Test=original_test, constantBaselineTest=baseline, teacherOracleTest=oracle,
                   selectedPresetTestSeeds=test_results, testMAEAcrossSeeds=spread,
                   promoted=promoted, maxEpochs=epochs,
                   notice='All data and targets are synthetic; teacher rules are exact by construction, not real-user feedback.')
    if promoted:
        chosen = Path(deployed['path'])
        checkpoint = torch.load(chosen, map_location='cpu', weights_only=True)
        checkpoint['metadata'].update(testMetrics=selected_test, testMAEAcrossSeeds=spread,
                                      evaluationProtocol=summary['protocol'], optimizationReport='output/matching_optimization/report.json')
        destination = ROOT / 'server' / 'models' / 'matching.pt'
        temporary = destination.with_suffix('.pt.tmp')
        torch.save(checkpoint, temporary)
        temporary.replace(destination)
        destination.with_suffix('.json').write_text(json.dumps(checkpoint['metadata'], ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('selectedPreset', 'selectedSeed', 'selectedTest', 'originalV1Test', 'testMAEAcrossSeeds', 'promoted')}, ensure_ascii=False, indent=2), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs', type=int, default=120)
    parser.add_argument('--output', type=Path, default=ROOT / 'output' / 'matching_optimization')
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('--epochs must be positive')
    run(args.output, args.epochs)
