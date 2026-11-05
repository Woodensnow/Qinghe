"""Follow-up study: explicit inputs, eligible pairs and seed ensembles.

The earlier exploratory test remains in its report. This study selects only on
validation, then uses a newly reserved confirmation split once for promotion.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

from train_matching import ROOT, DATA_SEED, train, partition, evaluate
from optimize_matching import load


def run(output, epochs=180, device='cpu'):
    import torch
    from matching_model import MatcherEnsemble
    from matching_data import synthetic_profiles
    from matching_evaluation import score_metrics
    torch.set_num_threads(2)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    runs, ensembles = [], {}
    for preset in ('wide_deep', 'wide_compact', 'wide_stable'):
        members, states, vocab = [], [], None
        for seed in (42, 7, 101):
            path = output / f'{preset}_{seed}.pt'
            report = train(path, epochs=epochs, seed=seed, preset=preset, patience=25, device=device)
            checkpoint, model = load(path)
            if vocab is not None:
                assert vocab == checkpoint['vocab']
            vocab = checkpoint['vocab']
            members.append(model)
            states.append(dict(weights=checkpoint['weights'], config=checkpoint['config']))
            record = dict(preset=preset, seed=seed, bestEpoch=report['bestEpoch'], stoppedEpoch=report['epochs'],
                          parameters=report['parameters'], validation=report['validationMetrics'])
            runs.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
        ensemble = MatcherEnsemble(members)
        validation = partition('validation', DATA_SEED, vocab=vocab)
        ensembles[preset] = dict(model=ensemble, states=states, vocab=vocab, validation=evaluate(ensemble, validation))
    def select_key(name):
        metrics = ensembles[name]['validation']
        return (-mean(metrics['ndcg5'][key] for key in ('mutualTraveler', 'mutualGuide')), metrics['eligibleMSE'])
    chosen = min(ensembles, key=select_key)
    selected = ensembles[chosen]
    # All model/configuration choices are frozen before building confirmation.
    confirmation = partition('confirmation', DATA_SEED, 64, 48, vocab=selected['vocab'])
    selected_metrics = evaluate(selected['model'], confirmation)
    old_checkpoint, original = load(ROOT / 'server' / 'models' / 'matching_v1.pt')
    old_confirmation = partition('confirmation', DATA_SEED, 64, 48, vocab=old_checkpoint['vocab'])
    original_metrics = evaluate(original, old_confirmation)
    training = partition('train', DATA_SEED, 96, 72)
    truth = confirmation['targets'].tolist()
    baseline = score_metrics([training['targets'].mean(0).tolist()] * len(truth), truth, confirmation['trips'], confirmation['guides'])
    oracle = score_metrics(truth, truth, confirmation['trips'], confirmation['guides'])
    seed_metrics = [evaluate(member, confirmation) for member in selected['model'].members]
    promoted = (all(selected_metrics['eligibleMAE'][key] < original_metrics['eligibleMAE'][key] for key in ('traveler', 'guide')) and
                all(selected_metrics['ndcg5'][key] >= original_metrics['ndcg5'][key] for key in ('mutualTraveler', 'mutualGuide')))
    profiles = synthetic_profiles(DATA_SEED + 3000, 64, 48, split='confirmation')
    manifest = dict(travelers=64, guides=48, pairs=3072,
                    sha256=hashlib.sha256(json.dumps(profiles, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
    summary = dict(protocol='v4 (text coverage + unknown-character augmentation): freeze 3 presets x 3 seeds; select ensemble on validation mutual NDCG@5; prospective confirmation after selection',
                   dataSeed=DATA_SEED, runs=runs, ensembleValidation={k: v['validation'] for k, v in ensembles.items()},
                   selectedPreset=chosen, confirmation=manifest, selectedConfirmation=selected_metrics,
                   originalV1Confirmation=original_metrics, constantBaselineConfirmation=baseline, teacherOracleConfirmation=oracle,
                   selectedSeedConfirmations=seed_metrics, promoted=promoted,
                   earlierExploratoryReport='output/matching_optimization/report.json',
                   notice='Synthetic rule distillation only; shared generator, structured categories and boilerplate remain across splits.')
    (output / 'report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if promoted:
        member_metadata = torch.load(output / f'{chosen}_42.pt', weights_only=True)['metadata']
        omitted = {'seed', 'epochs', 'bestEpoch', 'initialLoss', 'finalLoss', 'trainingMetrics', 'history', 'lossMetric'}
        metadata = {**{k: v for k, v in member_metadata.items() if k not in omitted},
                    'model': 'TinyTransformer-HeteroGNN-v4-ensemble', 'preset': chosen,
                    'seeds': [42, 7, 101], 'parameters': sum(p.numel() for p in selected['model'].parameters()),
                    'memberTraining': [{k: r[k] for k in ('seed', 'bestEpoch', 'stoppedEpoch', 'parameters')}
                                       for r in runs if r['preset'] == chosen],
                    'members': 3, 'selection': summary['protocol'], 'validationMetrics': selected['validation'],
                    'syntheticValidationMAE': selected['validation']['mae'], 'confirmationMetrics': selected_metrics,
                    'originalConfirmationMetrics': original_metrics, 'confirmationActors': manifest,
                    'optimizationReport': 'docs/matching_refinement_v4_report.json',
                    'notice': '合成规则蒸馏；三种子集成与独立模板确认，不代表真实用户接受概率。'}
        destination = ROOT / 'server' / 'models' / 'matching.pt'
        temporary = destination.with_suffix('.pt.tmp')
        torch.save(dict(kind='ensemble', members=selected['states'], vocab=selected['vocab'], metadata=metadata), temporary)
        temporary.replace(destination)
        destination.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('selectedPreset', 'selectedConfirmation', 'originalV1Confirmation', 'promoted')}, ensure_ascii=False, indent=2), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs', type=int, default=180)
    parser.add_argument('--device', choices=('auto', 'cpu', 'mps'), default='auto')
    parser.add_argument('--output', type=Path, default=ROOT / 'output' / 'matching_refinement_v4')
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('--epochs must be positive')
    run(args.output, args.epochs, args.device)
