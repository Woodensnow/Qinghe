"""Metrics against synthetic teacher scores; no acceptance probabilities."""
import math


def harmonic(left, right):
    return 2 * left * right / (left + right) if left + right else 0.0


def ndcg_at_k(predictions, relevance, k=5):
    """Continuous relevance, exponential gain, deterministic input-order ties."""
    def dcg(order):
        return sum((2 ** relevance[index] - 1) / math.log2(rank + 2) for rank, index in enumerate(order[:k]))
    ideal = dcg(sorted(range(len(relevance)), key=lambda i: -relevance[i]))
    if ideal == 0:
        return None
    return dcg(sorted(range(len(predictions)), key=lambda i: -predictions[i])) / ideal


def score_metrics(predictions, targets, trips, guides):
    """Regress all pairs; rank only city/language/service-compatible pairs.

    This synthetic benchmark has no date, booking or budget simulation, so its
    eligibility is explicitly narrower than production candidate().
    """
    n, m = len(trips), len(guides)
    errors = [[p[d] - t[d] for p, t in zip(predictions, targets)] for d in (0, 1)]
    metrics = dict(mse=sum(e * e for values in errors for e in values) / (2 * n * m),
                   mae={name: sum(abs(e) for e in values) / (n * m)
                        for name, values in zip(('traveler', 'guide'), errors)})
    eligible = [[t['city'] == g['city'] and bool(set(t['languages']) & set(g['languages'])) and
                 set(t['services']).issubset(g['services']) for g in guides] for t in trips]
    candidate_indices = [i * m + j for i in range(n) for j in range(m) if eligible[i][j]]
    metrics['eligibleMSE'] = sum(errors[d][i] ** 2 for d in (0, 1) for i in candidate_indices) / (2 * len(candidate_indices))
    metrics['eligibleMAE'] = {name: sum(abs(errors[d][i]) for i in candidate_indices) / len(candidate_indices)
                              for d, name in enumerate(('traveler', 'guide'))}
    metrics['eligiblePairs'] = len(candidate_indices)
    groups = {'traveler': [], 'guide': [], 'mutualTraveler': [], 'mutualGuide': []}
    for transpose, count_, candidates, direction, mutual_direction in (
            (False, n, m, 'traveler', 'mutualTraveler'), (True, m, n, 'guide', 'mutualGuide')):
        for row in range(count_):
            indices = [(column * m + row) if transpose else (row * m + column)
                       for column in range(candidates) if (eligible[column][row] if transpose else eligible[row][column])]
            if len(indices) < 2:
                continue
            axis = 1 if transpose else 0
            for name, scores, truth in (
                (direction, [predictions[i][axis] for i in indices], [targets[i][axis] for i in indices]),
                (mutual_direction, [harmonic(*predictions[i]) for i in indices], [harmonic(*targets[i]) for i in indices])):
                result = ndcg_at_k(scores, truth)
                if result is not None:
                    groups[name].append(result)
    metrics['ndcg5'] = {name: sum(values) / len(values) if values else None for name, values in groups.items()}
    metrics['rankQueries'] = {name: len(values) for name, values in groups.items()}
    return metrics
