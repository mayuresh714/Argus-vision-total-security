"""Extract and cache per-window embeddings for every video in a manifest."""
import hashlib
from pathlib import Path

import numpy as np

from .video import iter_windows


def cache_path(cache_dir, video_path, enc_name, cfg):
    key = hashlib.sha1(f"{video_path}|{enc_name}|{cfg}".encode()).hexdigest()[:16]
    return Path(cache_dir) / f"{key}.npz"


def extract(row, encoder, cache_dir, num_frames=16, sample_fps=4.0, stride_s=2.0):
    cfg = (num_frames, sample_fps, stride_s)
    cp = cache_path(cache_dir, row.video_path, encoder.name, cfg)
    if cp.exists():
        z = np.load(cp)
        return z["emb"], z["starts"], z["ends"]
    embs, starts, ends = [], [], []
    for w in iter_windows(row.video_path, num_frames, sample_fps, stride_s):
        embs.append(encoder.encode(w.frames))
        starts.append(w.start_s)
        ends.append(w.end_s)
    emb = np.stack(embs) if embs else np.zeros((0, 1), np.float32)
    cp.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cp, emb=emb, starts=np.array(starts), ends=np.array(ends))
    return emb, np.array(starts), np.array(ends)
