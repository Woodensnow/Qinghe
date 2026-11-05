"""Train with entity/template-held-out validation, early stop and best weights."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))

DATA_SEED = 31415
PRESETS = {
    'reference': dict(model=dict(dimension=32, graph_layers=2, dropout=0, head_dimension=64, feedforward=64), lr=.003, weight_decay=.001, ranking_weight=0),
    'compact': dict(model=dict(dimension=16, graph_layers=1, dropout=0, head_dimension=32, feedforward=32), lr=.003, weight_decay=.001, ranking_weight=0),
    'regularized': dict(model=dict(dimension=16, graph_layers=1, dropout=.15, head_dimension=32, feedforward=32), lr=.003, weight_decay=.01, ranking_weight=0),
    'lower_lr': dict(model=dict(dimension=16, graph_layers=1, dropout=.15, head_dimension=32, feedforward=32), lr=.001, weight_decay=.01, ranking_weight=0),
    'rank_aware': dict(model=dict(dimension=16, graph_layers=1, dropout=.15, head_dimension=32, feedforward=32), lr=.001, weight_decay=.01, ranking_weight=.05)
}
# v4 text settings: positions cover full real profiles; unknown-character
# augmentation for text outside the synthetic vocabulary.
TEXT = dict(max_length=256, unknown_rate=.15)
PRESETS.update({
    'wide_deep': dict(model=dict(dimension=32, graph_layers=2, dropout=.10, head_dimension=64, feedforward=64, compatibility_features=True, **TEXT), lr=.003, weight_decay=.01, ranking_weight=.02, eligible_only=True),
    'wide_compact': dict(model=dict(dimension=16, graph_layers=1, dropout=.10, head_dimension=32, feedforward=32, compatibility_features=True, **TEXT), lr=.003, weight_decay=.01, ranking_weight=.02, eligible_only=True),
    'wide_stable': dict(model=dict(dimension=32, graph_layers=1, dropout=.10, head_dimension=64, feedforward=64, compatibility_features=True, **TEXT), lr=.001, weight_decay=.01, ranking_weight=.02, eligible_only=True)
})


def resolve_device(name='auto'):
    import torch
    if name == 'auto':
        return 'mps' if torch.backends.mps.is_available() else 'cpu'
    if name == 'mps' and not torch.backends.mps.is_available():
        raise SystemExit('MPS is not available on this machine')
    return name


def to_device(value, device):
    if isinstance(value, dict):
        return {k: to_device(v, device) for k, v in value.items()}
    return value.to(device) if hasattr(value, 'to') else value


def cpu_state(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def partition(split, data_seed=DATA_SEED, travelers=32, guides=24, vocab=None):
    import torch
    from matching_data import synthetic_profiles, teaching_targets
    from matching_model import make_graph, tensor_graph, vocabulary
    offsets = dict(train=0, validation=1000, test=2000, confirmation=3000)
    trips, providers = synthetic_profiles(data_seed + offsets[split], travelers, guides, split=split)
    graph = make_graph(trips, providers)
    vocab = vocabulary([graph]) if vocab is None else vocab
    pairs, targets = [], []
    for trip in trips:
        for guide in providers:
            pairs.append([graph['indices'][('traveler', trip['id'])], graph['indices'][('guide', guide['id'])]])
            targets.append(teaching_targets(trip, guide))
    eligibility = [t['city'] == g['city'] and bool(set(t['languages']) & set(g['languages'])) and
                   set(t['services']).issubset(g['services']) for t in trips for g in providers]
    return dict(trips=trips, guides=providers, graph=graph, vocab=vocab, eligible=torch.tensor(eligibility),
                features=tensor_graph(graph, vocab), pairs=torch.tensor(pairs, dtype=torch.long), targets=torch.tensor(targets))


def evaluate(model, dataset):
    import torch
    from matching_evaluation import score_metrics
    model.eval()
    with torch.inference_mode():
        predictions = model(dataset['features'], dataset['pairs'])
    return score_metrics(predictions.tolist(), dataset['targets'].tolist(), dataset['trips'], dataset['guides'])


def ranking_loss(logits, targets, n, m, eligibility=None):
    """Sample comparisons in both directions; ignore near-tied teacher scores."""
    import torch
    values, truth = logits.reshape(n, m, 2), targets.reshape(n, m, 2)
    losses = []
    for direction, rows, columns in ((0, n, m), (1, m, n)):
        scores = values[:, :, direction] if direction == 0 else values[:, :, direction].T
        labels = truth[:, :, direction] if direction == 0 else truth[:, :, direction].T
        row = torch.randint(rows, (1024,), device=logits.device)
        first, second = torch.randint(columns, (2, 1024), device=logits.device)
        difference = labels[row, first] - labels[row, second]
        valid = difference.abs() >= .15
        if eligibility is not None:
            mask = eligibility.reshape(n, m) if direction == 0 else eligibility.reshape(n, m).T
            valid = valid & mask[row, first] & mask[row, second]
        margin = scores[row, first] - scores[row, second]
        weights = valid.float() * difference.abs()
        denominator = weights.sum() if eligibility is not None else valid.float().sum()
        losses.append((torch.nn.functional.softplus(-difference.sign() * margin) * weights).sum() / denominator.clamp_min(1))
    return sum(losses) / 2


def train(output, epochs=160, seed=42, travelers=96, guides=72, preset='wide_compact',
          data_seed=DATA_SEED, patience=20, encoder_layers=None, progress_every=0, device='cpu'):
    import torch
    from matching_model import TinyBilateralMatcher
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    settings = deepcopy(PRESETS[preset])
    if encoder_layers is not None:
        settings['model']['encoder_layers'] = encoder_layers
    criterion = 'eligibleMSE' if settings.get('eligible_only') else 'mse'
    device = resolve_device(device)
    keys = ('features', 'pairs', 'targets', 'eligible')
    training = partition('train', data_seed, travelers, guides)
    validation = partition('validation', data_seed, vocab=training['vocab'])
    for dataset in (training, validation):
        dataset.update({k: to_device(dataset[k], device) for k in keys})
    model = TinyBilateralMatcher(len(training['vocab']) + 2, **settings['model']).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=settings['lr'], weight_decay=settings['weight_decay'])
    history, best_loss, best_epoch, best_state = [], float('inf'), 0, None
    significant_loss, last_improvement = float('inf'), 0
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(training['features'], training['pairs'], return_logits=True)
        eligible = training['eligible'] if settings.get('eligible_only') else torch.ones(len(logits), dtype=torch.bool, device=device)
        loss = torch.nn.functional.mse_loss(logits[eligible].sigmoid(), training['targets'][eligible])
        if settings['ranking_weight']:
            loss = loss + settings['ranking_weight'] * ranking_loss(logits, training['targets'], travelers, guides,
                                                                     training['eligible'] if settings.get('eligible_only') else None)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        # Comparable metrics: dropout off, same definitions, on both partitions.
        train_metrics, val_metrics = evaluate(model, training), evaluate(model, validation)
        history.append(dict(epoch=epoch, trainMSE=train_metrics['mse'], validationMSE=val_metrics['mse'],
                            trainMAE=train_metrics['mae'], validationMAE=val_metrics['mae'],
                            trainEligibleMSE=train_metrics['eligibleMSE'], validationEligibleMSE=val_metrics['eligibleMSE']))
        if val_metrics[criterion] < best_loss:
            best_loss, best_epoch, best_state = val_metrics[criterion], epoch, cpu_state(model)
        if val_metrics[criterion] < significant_loss - .00001:
            significant_loss, last_improvement = val_metrics[criterion], epoch
        if progress_every and epoch % progress_every == 0:
            print(json.dumps(dict(seed=seed, epoch=epoch, trainMSE=train_metrics[criterion],
                                  validationMSE=val_metrics[criterion], bestEpoch=best_epoch)), flush=True)
        if patience is not None and epoch >= (60 if settings.get('eligible_only') else 20) and epoch - last_improvement >= patience:
            break
    last_weights = cpu_state(model) if patience is None else None
    model.load_state_dict(best_state)
    train_metrics, val_metrics = evaluate(model, training), evaluate(model, validation)
    from matching_evaluation import score_metrics
    mean = training['targets'].mean(0).tolist()
    model = model.cpu()
    baseline = score_metrics([mean] * len(validation['pairs']), validation['targets'].tolist(), validation['trips'], validation['guides'])
    metadata = dict(source='synthetic-demo', model='TinyTransformer-HeteroGNN-v2', seed=seed, dataSeed=data_seed,
                    epochs=len(history), maxEpochs=epochs, bestEpoch=best_epoch, preset=preset,
                    encoderLayers=settings['model'].get('encoder_layers', 1), trainingDevice=device,
                    selection='minimum validation ' + criterion + '; test set not used', torchVersion=str(torch.__version__),
                    trainActors=dict(travelers=travelers, guides=guides), validationActors=dict(travelers=32, guides=24),
                    trainPairs=len(training['pairs']), validationPairs=len(validation['pairs']),
                    lossMetric=criterion, initialLoss=history[0]['trainEligibleMSE' if settings.get('eligible_only') else 'trainMSE'],
                    finalLoss=train_metrics[criterion],
                    trainingMetrics=train_metrics, validationMetrics=val_metrics,
                    syntheticValidationMAE=val_metrics['mae'], constantBaselineMAE=baseline['mae'],
                    parameters=sum(p.numel() for p in model.parameters()), history=history,
                    notice='合成弱监督与分离模板验证；分数不是接受概率，真实推荐效果尚未验证。')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = dict(weights=model.state_dict(), vocab=training['vocab'], config=settings['model'],
                      trainingConfig=settings, metadata=metadata)
    if last_weights is not None:
        checkpoint['lastWeights'] = last_weights
    torch.save(checkpoint, output)
    output.with_suffix('.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs', type=int, default=160)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--data-seed', type=int, default=DATA_SEED)
    parser.add_argument('--preset', choices=PRESETS, default='wide_compact')
    parser.add_argument('--encoder-layers', type=int, default=1)
    parser.add_argument('--device', choices=('auto', 'cpu', 'mps'), default='auto')
    parser.add_argument('--output', type=Path, default=ROOT / 'output' / 'matching_training' / 'candidate.pt')
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error('--epochs must be positive')
    if args.encoder_layers < 1:
        parser.error('--encoder-layers must be positive')
    result = train(args.output, args.epochs, args.seed, preset=args.preset, data_seed=args.data_seed,
                   encoder_layers=args.encoder_layers, device=args.device)
    print(json.dumps({k: v for k, v in result.items() if k != 'history'}, ensure_ascii=False, indent=2))
