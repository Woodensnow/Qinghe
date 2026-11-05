"""Trainability, architecture contributions and reciprocal user workflows."""
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from test_server import ApiFixture
import matching_service
import store

HAS_TORCH = importlib.util.find_spec('torch') is not None


@unittest.skipUnless(HAS_TORCH, 'Install requirements-matching.txt for model tests')
class NeuralMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from matching_data import synthetic_profiles
        from matching_model import make_graph, tensor_graph
        cls.torch = torch
        cls.model, cls.vocab, cls.metadata = matching_service.load_engine()
        cls.trips, cls.guides = synthetic_profiles(seed=27, travelers=4, guides=3)
        cls.graph = make_graph(cls.trips, cls.guides)
        cls.features = tensor_graph(cls.graph, cls.vocab)
        cls.pairs = torch.tensor([[cls.graph['indices'][('traveler', t['id'])], cls.graph['indices'][('guide', g['id'])]] for t in cls.trips for g in cls.guides])

    def test_graph_has_typed_nodes_and_distinct_relation_parameters(self):
        from matching_model import NODE_TYPES, RELATIONS
        self.assertEqual({n['kind'] for n in self.graph['nodes']}, set(NODE_TYPES))
        layer = self.model.graph_layers[0]
        self.assertEqual(len(layer.relations), len(RELATIONS))
        self.assertIsNot(layer.relations['guide_interest'].weight, layer.relations['traveler_interest'].weight)
        self.assertNotIn('accepted', self.graph['edges'])
        for relation in ('traveler_city', 'guide_service', 'guide_interest'):
            self.assertEqual({(b, a) for a, b in self.graph['edges'][relation]}, set(self.graph['edges']['reverse_' + relation]))

    def test_both_text_and_graph_contribute_to_the_predictions(self):
        torch = self.torch
        with torch.inference_mode():
            full = self.model(self.features, self.pairs)
            no_graph = {**self.features, 'edges': {r: indices[:, :0] for r, indices in self.features['edges'].items()}}
            graph_removed = self.model(no_graph, self.pairs)
            # Replace sequence content, retaining node types and graph edges.
            no_text = {**self.features, 'tokens': torch.ones_like(self.features['tokens'])}
            text_removed = self.model(no_text, self.pairs)
        self.assertGreater(float((full - graph_removed).abs().max()), .0001)
        self.assertGreater(float((full - text_removed).abs().max()), .0001)
        self.assertTrue(torch.isfinite(full).all())

    def test_reordering_input_nodes_does_not_change_pair_scores(self):
        from matching_model import make_graph, tensor_graph
        graph = make_graph(self.trips[::-1], self.guides[::-1])
        pairs = self.torch.tensor([[graph['indices'][('traveler', t['id'])], graph['indices'][('guide', g['id'])]] for t in self.trips for g in self.guides])
        with self.torch.inference_mode():
            original = self.model(self.features, self.pairs)
            reordered = self.model(tensor_graph(graph, self.vocab), pairs)
        self.assertTrue(self.torch.allclose(original, reordered, atol=1e-5))

    def test_transformer_and_typed_edges_receive_training_gradients(self):
        self.model.zero_grad()
        loss = self.model(self.features, self.pairs).square().mean()
        loss.backward()
        attention = self.model.transformer.layers[0].self_attn.in_proj_weight.grad
        relation = self.model.graph_layers[0].relations['reverse_guide_interest'].weight.grad
        self.assertGreater(float(attention.abs().sum()), 0)
        self.assertGreater(float(relation.abs().sum()), 0)
        self.model.zero_grad()

    def test_a_new_model_can_train_and_save_reproducible_metadata(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
        from train_matching import train
        scratch = Path(__file__).resolve().parents[1] / 'tmp'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            output = Path(directory) / 'model.pt'
            report = train(output, epochs=30, seed=19, travelers=12, guides=8)
            self.assertLess(report['finalLoss'], report['initialLoss'])
            self.assertEqual(report['source'], 'synthetic-demo')
            self.assertEqual(report['trainPairs'], 96)
            checkpoint = self.torch.load(output, weights_only=True)
            self.assertEqual(checkpoint['metadata'], report)

    def test_reciprocal_score_does_not_hide_a_one_sided_match(self):
        from matching_model import reciprocal_score
        self.assertAlmostEqual(reciprocal_score(.9, .1), .18)
        self.assertGreater(reciprocal_score(.6, .6), reciprocal_score(.9, .1))


class MatchingFixture(ApiFixture):
    def setUp(self):
        super().setUp()
        self.owner = self.call('POST', '/api/auth/register', dict(name='苏州向导', email='matching-guide@example.cn', password='matching123'), expected=201)
        self.traveler = self.call('POST', '/api/auth/register', dict(name='咖啡旅人', email='matching-traveler@example.cn', password='matching123'), expected=201)
        self.guide = self.call('POST', '/api/guides', dict(name='苏州向导', city='苏州', headline='一起喝咖啡听老街里的历史故事',
                               bio='我在苏州生活了很多年，喜欢咖啡和老街，可以按照你的节奏定制轻松的路线。',
                               price=200, services=['城市漫步'], languages=['中文'], cover='/assets/images/guide-shanghai.jpg'), self.owner, 201)['guide']
        self.preferences = dict(maxPeople=4, weekdays=list(range(7)), blockedDates=[], interests=['咖啡', '历史'], paces=['慢慢逛'], text='喜欢有耐心、爱喝咖啡的旅人。')
        self.trip = dict(city='苏州', date=(date.today() + timedelta(days=13)).isoformat(), time='10:00', hours=4, people=2,
                         budget=400, services=['城市漫步'], languages=['中文'], interests=['咖啡'], paces=['慢慢逛'], description='希望喝咖啡逛老街。', share=True)

    def call(self, method, path, body=None, actor=None, expected=200):
        status, result, _ = self.request(method, path, body, token=actor['token'] if actor else None)
        self.assertEqual(status, expected, result)
        return result

    def save_preferences(self, **changes):
        self.preferences.update(changes)
        self.guide = self.call('PATCH', '/api/matching/preferences/' + self.guide['id'], self.preferences, self.owner)['guide']

    def save_trip(self, **changes):
        self.trip.update(changes)
        return self.call('POST', '/api/matching/trip', self.trip, self.traveler)['trip']


class MatchingRulesTests(MatchingFixture):
    def test_budget_uses_the_whole_group_and_missing_preferences_are_explicit(self):
        trip = self.save_trip()
        offer, reason = matching_service.candidate(trip, self.guide, store.data())
        self.assertIsNone(offer)
        self.assertEqual(reason, '地陪尚未填写双边偏好')
        self.save_preferences(maxPeople=8)
        trip = self.save_trip(people=5, budget=250)
        self.assertEqual(matching_service.candidate(trip, self.guide, store.data())[1], '超出整团总预算')
        trip = self.save_trip(budget=260)
        self.assertEqual(matching_service.candidate(trip, self.guide, store.data())[0]['total'], 260)

    def test_weekday_time_off_and_group_size_reflect_guide_constraints(self):
        trip = self.save_trip(people=5)
        self.save_preferences()
        self.assertEqual(matching_service.candidate(trip, self.guide, store.data())[1], '超出地陪接待人数')
        self.save_preferences(maxPeople=8, blockedDates=[trip['date']])
        self.assertEqual(matching_service.candidate(trip, self.guide, store.data())[1], '地陪当天休息')
        wrong_day = (date.fromisoformat(trip['date']).weekday() + 1) % 7
        self.save_preferences(blockedDates=[], weekdays=[wrong_day])
        self.assertEqual(matching_service.candidate(trip, self.guide, store.data())[1], '不在地陪接单星期内')

    def test_overlapping_booking_is_unavailable_until_cancelled(self):
        self.save_preferences()
        trip = self.save_trip()
        request = dict(guideId=self.guide['id'], packageId=self.guide['packages'][0]['id'], date=trip['date'], time='09:00', people=2)
        booking = self.call('POST', '/api/bookings', request, self.traveler, 201)['booking']
        self.assertEqual(matching_service.candidate(trip, self.guide, store.data())[1], '行程与已有预约重叠')
        other = self.call('POST', '/api/auth/register', dict(name='另一旅人', email='matching-other@example.cn', password='matching123'), expected=201)
        self.call('POST', '/api/bookings', {**request, 'time': '10:00'}, other, 409)
        self.call('PATCH', '/api/bookings/' + booking['id'] + '/cancel', actor=self.traveler)
        self.assertIsNotNone(matching_service.candidate(trip, self.guide, store.data())[0])


@unittest.skipUnless(HAS_TORCH, 'Install requirements-matching.txt for model integration tests')
class BilateralJourneys(MatchingFixture):
    def test_both_sides_see_the_same_score_and_provider_can_start_a_chat(self):
        self.save_preferences()
        trip = self.save_trip()
        forward = self.call('GET', '/api/matching/guides', actor=self.traveler)
        reverse = self.call('GET', '/api/matching/travelers?guideId=' + self.guide['id'], actor=self.owner)
        self.assertEqual(len(forward['matches']), 1)
        left, right = forward['matches'][0], reverse['matches'][0]
        self.assertEqual((left['score'], left['travelerScore'], left['guideScore']), (right['score'], right['travelerScore'], right['guideScore']))
        self.assertEqual(right['traveler']['name'], '咖啡旅人')
        self.assertNotIn('email', right['traveler'])
        self.assertEqual(forward['modelInfo']['source'], 'synthetic-demo')
        conversation = self.call('POST', '/api/matching/contact', dict(guideId=self.guide['id'], tripId=trip['id']), self.owner)
        endpoint = '/api/conversations/' + conversation['conversationId'] + '/messages'
        self.call('POST', endpoint, {'body': '看了你的行程，要不要去平江路喝咖啡？'}, self.owner, 201)
        messages = self.call('GET', endpoint, actor=self.traveler)['messages']
        self.assertEqual(messages[0]['senderRole'], 'guide')
        self.assertIn('平江路', messages[0]['body'])
        self.assertEqual(self.call('POST', '/api/matching/contact', dict(guideId=self.guide['id'], tripId=trip['id']), self.owner), conversation)

    def test_withdrawing_a_trip_stops_provider_recommendation(self):
        self.save_preferences()
        self.save_trip()
        self.assertEqual(len(self.call('GET', '/api/matching/travelers?guideId=' + self.guide['id'], actor=self.owner)['matches']), 1)
        self.call('DELETE', '/api/matching/trip', actor=self.traveler)
        self.assertIsNone(self.call('GET', '/api/matching/trip', actor=self.traveler)['trip'])
        self.assertEqual(self.call('GET', '/api/matching/travelers?guideId=' + self.guide['id'], actor=self.owner)['matches'], [])
