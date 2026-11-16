"""Novelty ("surprise") gate: how far is a window from this camera's normal?

Score = mean cosine distance to the k nearest embeddings in a bank built from
normal footage. This is encoder-agnostic. It is NOT V-JEPA's predictor error;
it is the simpler, robust baseline to beat before wiring the predictor in.
"""
import numpy as np
from sklearn.neighbors import NearestNeighbors


def _norm(x):
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-8)


class NormalBank:
    def __init__(self, k=5):
        self.k = k
        self.nn = None

    def fit(self, embs):
        x = _norm(np.asarray(embs, dtype=np.float32))
        self.k_eff = min(self.k, len(x))
        self.nn = NearestNeighbors(n_neighbors=self.k_eff, metric="cosine").fit(x)
        return self

    def score(self, embs, exclude_self=False):
        x = _norm(np.asarray(embs, dtype=np.float32))
        d, _ = self.nn.kneighbors(x)
        return d.mean(axis=1)
