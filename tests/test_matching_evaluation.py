"""Tests for data separation, ranking metrics and checkpoint selection."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server'))
from matching_data import (GUIDE_NOTES, INTERESTS, PACES, PHRASE_BANKS, TRAVELER_NOTES, synthetic_profiles,
                           teaching_targets)
from matching_evaluation import ndcg_at_k, score_metrics


class EvaluationProtocolTests(unittest.TestCase):
    def test_partitions_use_distinct_people_and_topic_sentences(self):
        identities, templates = [], []
        for split, seed in [('train', 100), ('validation', 1100), ('test', 2100)]:
            trips, guides = synthetic_profiles(seed, 12, 8, split=split)
            identities.append({item['id'] for item in trips + guides})
            templates.append({text for values in PHRASE_BANKS[split].values() for text in values})
        for i in range(3):
            for j in range(i + 1, 3):
                self.assertFalse(identities[i] & identities[j])
                self.assertFalse(templates[i] & templates[j])

    def test_teacher_labels_do_not_depend_on_reverse_parsing_a_template(self):
        trips, guides = synthetic_profiles(100, 2, 2)
        before = teaching_targets(trips[0], guides[0])
        guide = deepcopy(guides[0])
        guide['headline'] = '这是一种此前没有出现过的表达方式'
        self.assertEqual(teaching_targets(trips[0], guide), before)

    def test_free_text_filler_is_label_neutral_and_split_disjoint(self):
        words = INTERESTS + PACES + ['城市漫步', '美食探店', '接送陪同', '拍照陪游', '亲子出行', '周边包车', '苏州', '上海', '杭州']
        for banks in (GUIDE_NOTES, TRAVELER_NOTES):
            splits = list(banks)
            for split in splits:
                self.assertFalse([w for s in banks[split] for w in words if w in s])
                for other in splits[splits.index(split) + 1:]:
                    self.assertFalse(set(banks[split]) & set(banks[other]))
        # Filler uses its own generator, so labels match the text-free profiles.
        trips, guides = synthetic_profiles(100, 6, 4)
        self.assertTrue(any(len(g['bio']) > 40 for g in guides))
        with patch.dict(GUIDE_NOTES, train=['。']), patch.dict(TRAVELER_NOTES, train=['。']):
            plain_trips, plain_guides = synthetic_profiles(100, 6, 4)
        self.assertEqual([teaching_targets(t, g) for t in trips for g in guides],
                         [teaching_targets(t, g) for t in plain_trips for g in plain_guides])

    def test_ranking_metric_rewards_the_right_order(self):
        self.assertAlmostEqual(ndcg_at_k([.9, .1], [1, 0], k=1), 1)
        self.assertAlmostEqual(ndcg_at_k([.9, .1], [0, 1], k=1), 0)
        self.assertIsNone(ndcg_at_k([.9, .1], [0, 0]))

    def test_both_sides_and_joint_rankings_are_measured(self):
        trips = [dict(city='苏州', languages=['中文'], services=['城市漫步']) for _ in range(2)]
        guides = deepcopy(trips)
        labels = [[1., .6], [.2, .4], [.4, .8], [.9, .9]]
        metrics = score_metrics(labels, labels, trips, guides)
        self.assertEqual(metrics['mse'], 0)
        self.assertEqual(metrics['mae'], dict(traveler=0, guide=0))
        self.assertTrue(all(score == 1 for score in metrics['ndcg5'].values()))
        self.assertTrue(all(count == 2 for count in metrics['rankQueries'].values()))
        # When only one city-compatible candidate remains there is no useful
        # ordering experiment; it must not count as a perfect ranking query.
        guides[1]['city'] = '上海'
        metrics = score_metrics(labels, labels, trips, guides)
        self.assertEqual(metrics['rankQueries']['traveler'], 0)


@unittest.skipUnless(importlib.util.find_spec('torch'), 'Install matching dependencies')
class BestCheckpointTests(unittest.TestCase):
    def test_two_encoder_blocks_train_and_load_through_the_serving_loader(self):
        import torch
        import matching_service
        from matching_model import TinyBilateralMatcher, make_graph, tensor_graph, vocabulary
        trips, guides = synthetic_profiles(100, 2, 2)
        graph = make_graph(trips, guides)
        vocab = vocabulary([graph])
        features = tensor_graph(graph, vocab)
        pairs = torch.tensor([[graph['indices'][('traveler', trips[0]['id'])],
                               graph['indices'][('guide', guides[0]['id'])]]])
        config = dict(dimension=16, graph_layers=1, head_dimension=32, feedforward=32,
                      compatibility_features=True, encoder_layers=2)
        torch.manual_seed(53)
        model = TinyBilateralMatcher(len(vocab) + 2, **config).eval()
        first, second = model.transformer.layers
        self.assertFalse(torch.equal(first.self_attn.in_proj_weight, second.self_attn.in_proj_weight))
        expected = model(features, pairs)
        expected.square().mean().backward()
        for layer in model.transformer.layers:
            self.assertGreater(float(layer.self_attn.in_proj_weight.grad.abs().sum()), 0)
        scratch = ROOT / 'tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            checkpoint = Path(directory) / 'encoder2.pt'
            torch.save(dict(config=config, vocab=vocab, weights=model.state_dict(),
                            metadata={'encoderLayers': 2}), checkpoint)
            with patch.object(matching_service, 'MODEL_PATH', checkpoint), patch.object(matching_service, '_engine', None):
                loaded, _, metadata = matching_service.load_engine()
                self.assertEqual(metadata['encoderLayers'], 2)
                self.assertEqual(len(loaded.transformer.layers), 2)
                with torch.inference_mode():
                    actual = loaded(features, pairs)
                self.assertTrue(torch.allclose(actual, expected.detach(), atol=1e-6))

    def test_wide_features_use_observed_attributes_without_hidden_labels(self):
        import torch
        from matching_model import TinyBilateralMatcher, make_graph, tensor_graph, vocabulary
        trips, guides = synthetic_profiles(100, 2, 2)
        trips[0].update(interests=['咖啡'], paces=['慢慢逛'])
        guides[0]['matchPreferences'].update(interests=['咖啡'], paces=['慢慢逛'])
        graph = make_graph(trips, guides)
        changed = deepcopy(guides)
        changed[0]['expertiseInterests'] = ['自然']
        self.assertEqual(make_graph(trips, changed), graph)
        vocab = vocabulary([graph])
        features = tensor_graph(graph, vocab)
        pair = torch.tensor([[graph['indices'][('traveler', trips[0]['id'])], graph['indices'][('guide', guides[0]['id'])]]])
        torch.manual_seed(53)
        model = TinyBilateralMatcher(len(vocab) + 2, dimension=16, graph_layers=1, compatibility_features=True).eval()
        with torch.inference_mode():
            original = model(features, pair)
            different = {**features, 'attributes': {key: value.clone() for key, value in features['attributes'].items()}}
            different['attributes']['interests'][pair[0, 1]] = 0
            altered = model(different, pair)
        self.assertGreater(float((original - altered).abs().max()), .00001)

    def test_text_is_cut_to_model_capacity_and_unknown_noise_is_training_only(self):
        import torch
        from matching_model import TinyBilateralMatcher, make_graph, tensor_graph, vocabulary
        trips, guides = synthetic_profiles(100, 2, 2)
        graph = make_graph(trips, guides)
        vocab = vocabulary([graph])
        features = tensor_graph(graph, vocab)
        self.assertGreater(features['tokens'].shape[1], 16)
        torch.manual_seed(5)
        model = TinyBilateralMatcher(len(vocab) + 2, dimension=16, max_length=16, unknown_rate=.5)
        cut = {**features, 'tokens': features['tokens'][:, :16]}
        model.eval()
        with torch.inference_mode():
            self.assertTrue(torch.equal(model.encode(features)[0], model.encode(cut)[0]))
            self.assertTrue(torch.equal(model.encode(features)[0], model.encode(features)[0]))
        model.train()
        with torch.inference_mode():
            self.assertFalse(torch.equal(model.encode(features)[0], model.encode(features)[0]))

    def test_saved_weights_are_best_validation_epoch_not_last_epoch(self):
        sys.path.insert(0, str(ROOT / 'tools'))
        import torch
        from train_matching import train, partition, evaluate
        from matching_model import TinyBilateralMatcher
        scratch = ROOT / 'tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            path = Path(directory) / 'best.pt'
            report = train(path, epochs=24, seed=7, travelers=12, guides=8, patience=5)
            metric = 'validationEligibleMSE' if report['lossMetric'] == 'eligibleMSE' else 'validationMSE'
            expected = min(report['history'], key=lambda row: row[metric])
            self.assertEqual(report['bestEpoch'], expected['epoch'])
            checkpoint = torch.load(path, weights_only=True)
            model = TinyBilateralMatcher(len(checkpoint['vocab']) + 2, **checkpoint['config'])
            model.load_state_dict(checkpoint['weights'])
            validation = partition('validation', report['dataSeed'], vocab=checkpoint['vocab'])
            actual = evaluate(model, validation)
            self.assertAlmostEqual(actual[report['lossMetric']], expected[metric], places=7)
            self.assertNotIn('testMetrics', report)
