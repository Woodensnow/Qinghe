"""Train all three members for exactly 500 epochs and export both ensembles."""
import argparse
import json
from pathlib import Path

import torch

from train_matching import ROOT, DATA_SEED, evaluate, partition, train
from matching_model import MatcherEnsemble, TinyBilateralMatcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoder-layers', type=int, default=1)
    args = parser.parse_args()
    if args.encoder_layers < 1:
        parser.error('--encoder-layers must be positive')
    folder = 'matching_500' if args.encoder_layers == 1 else f'matching_500_encoder{args.encoder_layers}'
    output = ROOT / 'output' / folder
    output.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    summary = []
    for seed in (42, 7, 101):
        path = output / f'member_{seed}.pt'
        report = train(path, epochs=500, seed=seed, preset='wide_compact', patience=None,
                       encoder_layers=args.encoder_layers, progress_every=50)
        assert report['epochs'] == 500
        checkpoints.append(torch.load(path, map_location='cpu', weights_only=True))
        row = dict(seed=seed, epochs=500, encoderLayers=args.encoder_layers, bestEpoch=report['bestEpoch'],
                   bestValidationMSE=report['validationMetrics']['eligibleMSE'],
                   lastValidationMSE=report['history'][-1]['validationEligibleMSE'])
        summary.append(row)
        print(json.dumps(row), flush=True)
    vocab = checkpoints[0]['vocab']
    validation = partition('validation', DATA_SEED, vocab=vocab)
    comparison = {}
    for label, key in [('best', 'weights'), ('epoch500', 'lastWeights')]:
        members, states = [], []
        for checkpoint in checkpoints:
            assert vocab == checkpoint['vocab']
            model = TinyBilateralMatcher(len(vocab) + 2, **checkpoint['config'])
            model.load_state_dict(checkpoint[key])
            members.append(model)
            states.append(dict(config=checkpoint['config'], weights=checkpoint[key]))
        metrics = evaluate(MatcherEnsemble(members), validation)
        metadata = dict(model=f'TinyTransformer-HeteroGNN-encoder{args.encoder_layers}-500-' + label, source='synthetic-demo',
                        encoderLayers=args.encoder_layers,
                        epochsPerMember=500, selection=label, memberTraining=summary,
                        validationMetrics=metrics, notice='合成验证结果，分数不是接受概率。')
        torch.save(dict(kind='ensemble', members=states, vocab=vocab, metadata=metadata),
                   output / f'ensemble_{label}.pt')
        comparison[label] = metrics
    (output / 'report.json').write_text(json.dumps(dict(encoderLayers=args.encoder_layers, members=summary, validation=comparison),
                                                   ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
