"""Compare fixed one/two-layer 500-epoch experiments and CPU latency."""
import json
from pathlib import Path
import statistics
import time

import torch

from train_matching import ROOT, partition, evaluate
from matching_model import TinyBilateralMatcher, MatcherEnsemble

SEEDS = (42, 7, 101)
EVALUATION_DATA_SEED = 271828


def load_ensemble(folder, weight_key='weights'):
    members, checkpoints = [], []
    for seed in SEEDS:
        checkpoint = torch.load(folder / f'member_{seed}.pt', map_location='cpu', weights_only=True)
        model = TinyBilateralMatcher(len(checkpoint['vocab']) + 2, **checkpoint['config'])
        model.load_state_dict(checkpoint[weight_key])
        members.append(model)
        checkpoints.append(checkpoint)
    return MatcherEnsemble(members).eval(), checkpoints


def benchmark(model, dataset):
    pairs = dataset['pairs'][dataset['eligible']]
    with torch.inference_mode():
        for _ in range(5):
            model(dataset['features'], pairs)
        samples = []
        for _ in range(20):
            start = time.perf_counter()
            model(dataset['features'], pairs)
            samples.append(1000 * (time.perf_counter() - start))
    return dict(medianMs=statistics.median(samples), iterations=20,
                scoredPairs=len(pairs), scope='warm CPU forward; excludes loading, graph building and HTTP')


def compare():
    torch.set_num_threads(2)
    output = ROOT / 'output' / 'matching_500_encoder2'
    reports = {}
    reference_config = None
    reference_vocab = None
    for depth, folder in [(1, ROOT / 'output' / 'matching_500'), (2, output)]:
        ensemble, checkpoints = load_ensemble(folder)
        config = {k: v for k, v in checkpoints[0]['config'].items() if k != 'encoder_layers'}
        if reference_config is not None:
            assert config == reference_config
            assert checkpoints[0]['vocab'] == reference_vocab
        reference_config, reference_vocab = config, checkpoints[0]['vocab']
        for member, checkpoint in zip(ensemble.members, checkpoints):
            assert checkpoint['metadata']['epochs'] == 500
            assert len(member.transformer.layers) == depth
        validation = partition('validation', checkpoints[0]['metadata']['dataSeed'], vocab=reference_vocab)
        # New identities, shared confirmation-template family. This does not
        # establish real-user or unseen-template performance.
        evaluation = partition('confirmation', EVALUATION_DATA_SEED, 64, 48, vocab=reference_vocab)
        last, _ = load_ensemble(folder, 'lastWeights')
        reports[str(depth)] = dict(encoderLayers=depth,
                                  parameters=sum(p.numel() for p in ensemble.parameters()),
                                  members=[dict(seed=c['metadata']['seed'], epochs=c['metadata']['epochs'],
                                                bestEpoch=c['metadata']['bestEpoch']) for c in checkpoints],
                                  bestValidation=evaluate(ensemble, validation),
                                  lastValidation=evaluate(last, validation),
                                  freshSyntheticEvaluation=evaluate(ensemble, evaluation),
                                  seedEvaluation=[evaluate(m, evaluation) for m in ensemble.members],
                                  inference=benchmark(ensemble, evaluation))
    result = dict(protocol='Same data, seeds, hyperparameters and 500-epoch budget; validation-best checkpoints per member',
                  evaluationDataSeed=EVALUATION_DATA_SEED,
                  evaluationScope='New synthetic identities; previously used confirmation-template family and rule generator',
                  models=reports)
    path = output / 'depth_comparison.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    compare()
