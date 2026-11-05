"""Small trainable Transformer + relation-specific heterogeneous GNN.

PyTorch only: no pretrained download, PyG, or remote inference service.
"""
import torch
from torch import nn
from matching_data import INTERESTS, PACES

SERVICES = ('城市漫步', '美食探店', '接送陪同', '拍照陪游', '亲子出行', '周边包车')

NODE_TYPES = ('traveler', 'guide', 'city', 'service', 'language', 'interest', 'pace')
FORWARD_RELATIONS = ('traveler_city', 'guide_city', 'traveler_service', 'guide_service',
                     'traveler_language', 'guide_language', 'traveler_interest',
                     'guide_interest', 'traveler_pace', 'guide_pace')
RELATIONS = FORWARD_RELATIONS + tuple('reverse_' + r for r in FORWARD_RELATIONS)


def profile_text(item, role):
    preferences = item if role == 'traveler' else item.get('matchPreferences', {})
    return ' '.join([item['city'], ' '.join(item.get('services', [])),
                     ' '.join(item.get('languages', [])), ' '.join(preferences.get('interests', [])),
                     ' '.join(preferences.get('paces', [])), preferences.get('text', ''),
                     item.get('description', ''), item.get('headline', ''), item.get('bio', '')])


def make_graph(travelers, guides):
    """Create only attribute edges, never target/recommendation/label edges."""
    nodes, indices, edges = [], {}, {r: [] for r in RELATIONS}

    def node(kind, identifier, text):
        key = (kind, identifier)
        if key not in indices:
            indices[key] = len(nodes)
            nodes.append(dict(kind=kind, text=text))
        return indices[key]

    for role, items in (('traveler', travelers), ('guide', guides)):
        for item in items:
            source = node(role, item['id'], profile_text(item, role))
            preferences = item if role == 'traveler' else item.get('matchPreferences', {})
            nodes[source]['attributes'] = dict(services=item.get('services', []),
                                               interests=preferences.get('interests', []), paces=preferences.get('paces', []))
            attributes = [('city', [item['city']]), ('service', item.get('services', [])),
                          ('language', item.get('languages', [])),
                          ('interest', preferences.get('interests', [])),
                          ('pace', preferences.get('paces', []))]
            for kind, values in attributes:
                for value in dict.fromkeys(values):
                    target = node(kind, value, value)
                    relation = role + '_' + kind
                    edges[relation].append((source, target))
                    edges['reverse_' + relation].append((target, source))
    return dict(nodes=nodes, indices=indices, edges=edges)


def vocabulary(graphs):
    chars = sorted({char for graph in graphs for node in graph['nodes'] for char in node['text']})
    return {char: i + 2 for i, char in enumerate(chars)}


def tensor_graph(graph, vocab, max_length=512):
    # Memory guard only: each model truncates to its own position capacity.
    texts = [[vocab.get(c, 1) for c in n['text'][:max_length]] or [1] for n in graph['nodes']]
    length = max(map(len, texts))
    tokens = torch.zeros(len(texts), length, dtype=torch.long)
    for row, ids in enumerate(texts):
        tokens[row, :len(ids)] = torch.tensor(ids)
    attributes = {key: torch.tensor([[float(value in node.get('attributes', {}).get(key, [])) for value in values]
                                     for node in graph['nodes']])
                  for key, values in [('services', SERVICES), ('interests', INTERESTS), ('paces', PACES)]}
    return dict(tokens=tokens, attributes=attributes, types=torch.tensor([NODE_TYPES.index(n['kind']) for n in graph['nodes']]),
                edges={r: torch.tensor(values, dtype=torch.long).reshape(-1, 2).T for r, values in graph['edges'].items()})


class HeterogeneousLayer(nn.Module):
    def __init__(self, dimension, dropout=0):
        super().__init__()
        self.self_projection = nn.Linear(dimension, dimension)
        self.relations = nn.ModuleDict({r: nn.Linear(dimension, dimension, bias=False) for r in RELATIONS})
        self.norm = nn.LayerNorm(dimension)
        self.dropout = nn.Dropout(dropout)

    def forward(self, features, edges):
        messages = torch.zeros_like(features)
        degree = torch.zeros(features.shape[0], 1, device=features.device)
        for relation, indices in edges.items():
            if indices.shape[1]:
                source, target = indices
                messages.index_add_(0, target, self.relations[relation](features[source]))
                degree.index_add_(0, target, torch.ones(len(target), 1, device=features.device))
        return self.norm(features + self.dropout(torch.relu(self.self_projection(features) + messages / degree.clamp_min(1))))


class TinyBilateralMatcher(nn.Module):
    def __init__(self, vocab_size, dimension=32, max_length=128, graph_layers=2,
                 dropout=0, head_dimension=64, feedforward=64, compatibility_features=False,
                 encoder_layers=1, unknown_rate=0):
        super().__init__()
        # Training-only: replace this share of characters with the unknown id so
        # the encoder tolerates real text that is mostly outside the vocabulary.
        self.unknown_rate = unknown_rate
        self.tokens = nn.Embedding(vocab_size, dimension, padding_idx=0)
        self.positions = nn.Embedding(max_length, dimension)
        self.types = nn.Embedding(len(NODE_TYPES), dimension)
        encoder_config = dict(d_model=dimension, nhead=4, dim_feedforward=feedforward,
                              dropout=dropout, batch_first=True, activation='gelu')
        layer = nn.TransformerEncoderLayer(**encoder_config)
        self.transformer = nn.TransformerEncoder(layer, num_layers=encoder_layers, enable_nested_tensor=False)
        # Encoder clones share initial values by default. Initialize each added
        # block independently while preserving the original one-layer setup.
        for index in range(1, encoder_layers):
            self.transformer.layers[index] = nn.TransformerEncoderLayer(**encoder_config)
        self.graph_layers = nn.ModuleList([HeterogeneousLayer(dimension, dropout) for _ in range(graph_layers)])
        self.head_dropout = nn.Dropout(dropout)
        self.compatibility_features = compatibility_features
        input_width = 6 * dimension + (4 if compatibility_features else 0)
        # Independent heads learn traveler-to-guide and guide-to-traveler scores.
        self.traveler_head = nn.Sequential(nn.Linear(input_width, head_dimension), nn.GELU(), nn.Linear(head_dimension, 1))
        self.guide_head = nn.Sequential(nn.Linear(input_width, head_dimension), nn.GELU(), nn.Linear(head_dimension, 1))

    def encode(self, graph):
        tokens = graph['tokens'][:, :self.positions.num_embeddings]
        mask = tokens.eq(0)
        if self.training and self.unknown_rate:
            tokens = tokens.masked_fill(~mask & (torch.rand(tokens.shape, device=tokens.device) < self.unknown_rate), 1)
        positions = torch.arange(tokens.shape[1], device=tokens.device)
        sequence = self.tokens(tokens) + self.positions(positions)
        sequence = self.transformer(sequence, src_key_padding_mask=mask)
        raw = (sequence * (~mask).unsqueeze(-1)).sum(1) / (~mask).sum(1, keepdim=True)
        raw = raw + self.types(graph['types'])
        features = raw
        for layer in self.graph_layers:
            features = layer(features, graph['edges'])
        return raw, features

    def forward(self, graph, pairs, return_logits=False):
        raw, features = self.encode(graph)
        travelers, guides = pairs[:, 0], pairs[:, 1]
        combined = torch.cat([raw[travelers], raw[guides], features[travelers], features[guides],
                              raw[travelers] * raw[guides], features[travelers] * features[guides]], dim=-1)
        if self.compatibility_features:
            attributes = graph['attributes']
            services_t, services_g = attributes['services'][travelers], attributes['services'][guides]
            interests_t, interests_g = attributes['interests'][travelers], attributes['interests'][guides]
            intersection = (interests_t * interests_g).sum(1)
            explicit = torch.stack([(services_t * services_g).sum(1) / services_t.sum(1).clamp_min(1),
                                    intersection / interests_t.sum(1).clamp_min(1),
                                    intersection / interests_g.sum(1).clamp_min(1),
                                    ((attributes['paces'][travelers] * attributes['paces'][guides]).sum(1) > 0).float()], dim=1)
            combined = torch.cat([combined, explicit], dim=1)
        combined = self.head_dropout(combined)
        logits = torch.cat([self.traveler_head(combined), self.guide_head(combined)], dim=1)
        return logits if return_logits else logits.sigmoid()


class MatcherEnsemble(nn.Module):
    """Average independent seeds with identical vocabulary and architecture."""
    def __init__(self, members):
        super().__init__()
        self.members = nn.ModuleList(members)

    @property
    def transformer(self):
        return self.members[0].transformer

    @property
    def graph_layers(self):
        return self.members[0].graph_layers

    def forward(self, graph, pairs):
        return torch.stack([model(graph, pairs) for model in self.members]).mean(0)


def reciprocal_score(traveler, guide):
    """Harmonic mean penalizes a one-sided recommendation; not a probability."""
    return 0.0 if traveler + guide == 0 else 2 * traveler * guide / (traveler + guide)
