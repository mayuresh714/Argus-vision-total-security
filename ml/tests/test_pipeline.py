import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from argus_ml.encoders import StandInEncoder
from argus_ml.evaluate import alerts_from_scores, run_eval, threshold_for_budget
from argus_ml.manifest import load_manifest, write_manifest
from argus_ml.synthetic import make_dataset


def test_alert_cooldown_merges():
    st = np.arange(0, 100, 2.0); sc = np.zeros(50); sc[10:20] = 1
    assert len(alerts_from_scores(st, sc, 0.5, cooldown_s=30)) == 1
    assert len(alerts_from_scores(st, sc, 0.5, cooldown_s=0)) == 10


def test_threshold_respects_budget():
    st = np.arange(0, 86400, 2.0); sc = np.random.default_rng(0).random(len(st))
    tau = threshold_for_budget([(st, sc)], 24.0, 5, 30)
    n = len(alerts_from_scores(st, sc, tau, 30))
    assert 0 < n <= 5


def test_manifest_roundtrip(tmp_path):
    rows = make_dataset(tmp_path / "d", sites=1, normals_per_site=1, events_per_site=1)
    write_manifest(rows, tmp_path / "m.csv")
    back = load_manifest(tmp_path / "m.csv")
    assert [r.label for r in back] == ["normal", "theft"] and back[1].event_start == 14.0


def test_end_to_end_synthetic_separates(tmp_path):
    rows = make_dataset(tmp_path / "d", sites=5, normals_per_site=4, events_per_site=2)
    for proto in ("global", "per-site"):
        rep = run_eval(rows, StandInEncoder(), tmp_path / "c", protocol=proto, budgets=(2, 10))
        assert rep["video_auroc"] > 0.9, (proto, rep["video_auroc"])
        assert rep["by_budget"]["10"]["event_recall"] >= 0.5
