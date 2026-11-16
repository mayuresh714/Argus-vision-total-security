"""Evaluation: does the novelty gate separate events from normal footage,
and at what false-alarm cost?

Protocols
  global    bank = normal footage from TRAIN sites; test on UNSEEN sites.
            Measures how well a gate generalises to a camera it has never seen.
  per-site  bank = other normal videos from the SAME site (leave-one-video-out).
            Mimics the product: calibrate on a camera's first days, then watch.

Alert thresholds are chosen on calibration (normal-only, leave-one-out) scores
for a false-alarm budget, never on the test videos.
"""
import numpy as np
from sklearn.metrics import roc_auc_score

from .features import extract
from .novelty import NormalBank


def alerts_from_scores(starts, scores, tau, cooldown_s):
    """Merge flagged windows into alerts, with a cooldown between alerts."""
    out, last = [], -1e18
    for t, s in zip(starts, scores):
        if s >= tau and t - last >= cooldown_s:
            out.append(float(t))
            last = t
    return out


def _overlap(a0, a1, b0, b1):
    return a0 <= b1 and b0 <= a1


def split_sites(rows, test_frac=0.4, seed=0):
    sites = sorted({r.site_id for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(sites)
    n_test = max(1, int(round(len(sites) * test_frac)))
    test = set(sites[:n_test])
    return set(sites) - test, test


def threshold_for_budget(cal_scores, cal_hours, budget_per_day, cooldown_s):
    """Lowest threshold whose alerts/day on calibration footage <= budget.

    Binary search on the sorted unique scores, then step up until the budget
    really holds (cooldown makes the alert count only roughly monotone)."""
    cands = np.unique(np.concatenate([s for _, s in cal_scores]))

    def ok(tau):
        n = sum(len(alerts_from_scores(st, sc, tau, cooldown_s)) for st, sc in cal_scores)
        return cal_hours > 0 and n / cal_hours * 24 <= budget_per_day

    lo, hi = 0, len(cands)
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(cands[mid]):
            hi = mid
        else:
            lo = mid + 1
    while lo < len(cands) and not ok(cands[lo]):
        lo += 1
    return float(cands[lo]) if lo < len(cands) else float(cands.max()) + 1e-6


def run_eval(rows, encoder, cache_dir, protocol="global", k=5, cooldown_s=30.0,
             budgets=(1, 2, 5, 10), test_frac=0.4, seed=0, **win):
    feats = {}
    for r in rows:
        emb, st, en = extract(r, encoder, cache_dir, **win)
        if len(emb) == 0:
            continue
        feats[r.video_path] = (emb, np.asarray(st), np.asarray(en))
    rows = [r for r in rows if r.video_path in feats]
    normals = [r for r in rows if r.is_normal]
    if not normals:
        raise SystemExit("manifest has no normal videos: cannot calibrate")

    if protocol == "global":
        train_sites, test_sites = split_sites(rows, test_frac, seed)
        bank_rows = [r for r in normals if r.site_id in train_sites]
        if not bank_rows:
            raise SystemExit("no normal footage in train sites")
        test_rows = [r for r in rows if r.site_id in test_sites]
        cal_rows = bank_rows
    elif protocol == "per-site":
        test_rows = rows
        cal_rows = normals
    else:
        raise ValueError(protocol)

    def bank_for(row):
        if protocol == "global":
            pool = bank_rows
        else:
            pool = [n for n in normals if n.site_id == row.site_id and n.video_path != row.video_path]
        if not pool:
            return None
        return NormalBank(k).fit(np.concatenate([feats[n.video_path][0] for n in pool]))

    global_bank = bank_for(None) if protocol == "global" else None

    def score_video(r, loo=False):
        if protocol == "global":
            if loo:  # calibration: leave this video out of the global bank
                pool = [n for n in bank_rows if n.video_path != r.video_path]
                if not pool:
                    return None
                b = NormalBank(k).fit(np.concatenate([feats[n.video_path][0] for n in pool]))
            else:
                b = global_bank
        else:
            b = bank_for(r)
        return None if b is None else b.score(feats[r.video_path][0])

    cal = []
    for r in cal_rows:
        s = score_video(r, loo=True)
        if s is not None:
            cal.append((feats[r.video_path][1], s, (feats[r.video_path][2][-1]) / 3600.0))
    cal_scores = [(st, s) for st, s, _ in cal]
    cal_hours = sum(h for *_, h in cal)

    ev = []
    for r in test_rows:
        s = score_video(r)
        if s is None:
            continue
        ev.append((r, feats[r.video_path][1], feats[r.video_path][2], s))

    pos = [e for e in ev if not e[0].is_normal]
    neg = [e for e in ev if e[0].is_normal]
    report = {"protocol": protocol, "encoder": encoder.name, "n_test_videos": len(ev),
              "n_anomalous": len(pos), "n_normal": len(neg), "cal_hours": round(cal_hours, 3)}
    if pos and neg:
        report["video_auroc"] = float(roc_auc_score(
            [0] * len(neg) + [1] * len(pos),
            [e[3].max() for e in neg] + [e[3].max() for e in pos]))

    ys, ss = [], []
    for r, st, en, s in ev:
        if r.is_normal:
            ys += [0] * len(s); ss += list(s)
        elif r.event_start is not None:
            for a, b, v in zip(st, en, s):
                ys.append(int(_overlap(a, b, r.event_start, r.event_end))); ss.append(v)
    if len(set(ys)) == 2:
        report["window_auroc"] = float(roc_auc_score(ys, ss))

    report["by_budget"] = {}
    report["warnings"] = []
    for bud in budgets:
        if cal_hours * bud / 24 < 1:
            report["warnings"].append(
                f"budget {bud}/day needs >= {24 / bud:.1f} h of calibration normals to resolve; "
                f"have {cal_hours:.2f} h, so this row is not trustworthy")
        tau = threshold_for_budget(cal_scores, cal_hours, bud, cooldown_s)
        det, ttas, per_class = 0, [], {}
        for r, st, en, s in pos:
            flagged = [(a, b) for a, b, v in zip(st, en, s) if v >= tau]
            if r.event_start is not None:
                hit = [(a, b) for a, b in flagged if _overlap(a, b, r.event_start, r.event_end)]
            else:
                hit = flagged
            ok = bool(hit)
            det += ok
            c = per_class.setdefault(r.label, [0, 0]); c[0] += ok; c[1] += 1
            if ok and r.event_start is not None:
                ttas.append(max(0.0, hit[0][0] - r.event_start))
        n_fa = sum(len(alerts_from_scores(st, s, tau, cooldown_s)) for _, st, _, s in neg)
        hrs = sum(en[-1] for _, _, en, _ in neg) / 3600.0
        report["by_budget"][str(bud)] = {
            "threshold": tau,
            "event_recall": det / len(pos) if pos else None,
            "false_alerts_per_day_on_test_normals": (n_fa / hrs * 24) if hrs else None,
            "median_time_to_alert_s": float(np.median(ttas)) if ttas else None,
            "recall_by_class": {k_: v[0] / v[1] for k_, v in per_class.items()},
        }
    report["_scores"] = ev
    return report
