import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save_report(report, out_dir):
    from pathlib import Path
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    ev = report.pop("_scores")
    (out / "metrics.json").write_text(json.dumps(report, indent=2))

    normal = np.concatenate([e[3] for e in ev if e[0].is_normal] or [np.zeros(1)])
    anom_ev, anom_other = [], []
    for r, st, en, s in ev:
        if r.is_normal:
            continue
        for a, b, v in zip(st, en, s):
            inside = r.event_start is not None and a <= r.event_end and r.event_start <= b
            (anom_ev if inside or r.event_start is None else anom_other).append(v)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    bins = np.linspace(0, max(normal.max(), max(anom_ev or [0]), 1e-6), 40)
    ax[0].hist(normal, bins, alpha=.6, label="normal windows", density=True)
    if anom_ev:
        ax[0].hist(anom_ev, bins, alpha=.6, label="event windows", density=True)
    ax[0].set_xlabel("novelty score"); ax[0].legend(); ax[0].set_title("Score separation")
    b = report["by_budget"]
    xs = [float(k) for k in b]; ys = [b[k]["event_recall"] or 0 for k in b]
    ax[1].plot(xs, ys, "o-"); ax[1].set_ylim(0, 1.05)
    ax[1].set_xlabel("false-alert budget (per camera-day)"); ax[1].set_ylabel("event recall")
    ax[1].set_title("Recall vs false-alert budget")
    fig.tight_layout(); fig.savefig(out / "report.png", dpi=130)
    return out
