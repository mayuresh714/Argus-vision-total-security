# 🧪 Argus ML

Test whether a video "novelty gate" can tell theft-like events from normal camera footage, and at what false-alarm cost, **before** building product around it.

The gate scores each ~4 s window by how far it is from that camera's normal footage. High score = something unusual = wake the expensive model.

## What works today

| Piece | Status |
|---|---|
| Manifest format, video windowing, embedding cache | ✅ tested |
| Novelty gate (k-nearest-neighbour distance to a bank of normal footage) | ✅ tested |
| Evaluation: video/window AUROC, event recall at a false-alert budget, time-to-alert, per-class recall | ✅ tested |
| Two protocols: unseen camera (`global`) and calibrate-on-this-camera (`per-site`) | ✅ tested |
| Synthetic data generator + UCF-Crime manifest builder | ✅ generator tested, UCF builder untested (no data reachable) |
| Real V-JEPA 2 encoder | ⚠️ written, **never run**: needs a GPU and Hugging Face access. Run `scripts/check_encoder.py` first |
| V-JEPA *predictor-error* surprise | ❌ not built. Current gate is the simpler embedding-distance baseline; beat that first |
| Trained classifier head, VLM arbiter, distillation | ❌ not built |

Results on the synthetic set (perfect scores) only prove the harness runs. They say nothing about real theft.

## Run it

```bash
cd ml && pip install -r requirements.txt

# 1. prove the harness works (no GPU, no downloads)
python scripts/make_synthetic.py --out data/synthetic
python scripts/run_eval.py --manifest data/synthetic/manifest.csv --protocol per-site
pytest -q tests

# 2. real run (GPU or Colab): add torch + transformers>=4.53
python scripts/check_encoder.py                      # sanity check the encoder
python scripts/build_ucf_manifest.py --root /path/to/UCF-Crime
python scripts/run_eval.py --manifest data/ucf_manifest.csv --encoder vjepa2 --protocol global
```

Output: `reports/latest/metrics.json` and `report.png`.

## Your own clips

One CSV row per video (`data/manifest_template.csv`):

```
video_path,label,site_id,event_start,event_end,source,license
clips/a.mp4,theft,shopA,12.0,31.5,youtube:<id>,unknown
clips/b.mp4,normal,shopA,,,own-pilot,owned
```

- `site_id` matters: results are split by camera, never by random clip.
- Leave `event_start/end` blank for weak (video-level) labels.
- Fill `source` and `license` so you know what you can use later.

## Public datasets

I could not download any of these from my environment, so none are verified by me. **Check each license before use.**

| Dataset | What it gives you | Notes |
|---|---|---|
| [UCF-Crime](https://www.crcv.ucf.edu/projects/real-world/) | 1,900 untrimmed surveillance videos, 13 classes incl. burglary, robbery, shoplifting; ~128 h | Video-level labels. Sources disagree on its license (CC0 / "other" / unstated): confirm on the official page. Has ~950 normal videos |
| [UCA](https://www.crcv.ucf.edu/chenchen/datasets/) annotations | Event times and text for 1,854 UCF-Crime videos | Add-on labels, not videos |
| [UCFCrime2Local](https://aimagelab.ing.unimore.it/imagelab/page.asp?IdPage=30) | Spatio-temporal annotations for UCF-Crime | Annotations only |
| [CamNuvem](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9784719/) | 486 robbery surveillance videos from public sources | Weak labels, 2022 |
| [Shoplifting (Mendeley)](https://data.mendeley.com/datasets/3pn2rnv2wg/1) | Shoplifting set | The listing showed metadata only; confirm files exist |
| [UBnormal](https://github.com/lilygeorgescu/UBnormal) | Synthetic anomaly videos | Rendered, not real CCTV |
| ShanghaiTech, CUHK Avenue, NWPU-Campus, XD-Violence | Mostly extra normal footage and generic anomalies | License terms not found |

Limits to keep in mind:
- Public sets have **no camera/site ids**. UCF-Crime videos are treated as one pseudo-site each, so only the `global` protocol is meaningful on them.
- Most public footage is dramatic and well lit. Expect real-shop performance to be lower.
- The most valuable data is **hours of normal footage from the cameras you'll deploy on**. Public data can't replace that.
- Scraped YouTube/Twitter clips: using them to evaluate internally is lower risk than training and shipping a model on them. Get legal advice first.

## How to read the results

- `video_auroc`, `window_auroc`: does the gate separate event from normal at all?
- `by_budget`: event recall when the threshold is set so normal footage triggers at most N alerts per camera-day. The threshold comes from calibration footage, never the test set.
- `warnings`: a budget of N/day needs at least 24/N hours of normal footage to measure. If you see a warning, collect more normals.
- Credible numbers need roughly 200+ labeled events across 30+ sites and hundreds of normal hours.

## Next steps

1. Run on UCF-Crime with V-JEPA 2 and compare against the `standin` baseline and plain motion.
2. Add the predictor-error score and see if it beats embedding distance.
3. Train a small classifier head on frozen features for the labeled classes.
4. Shadow-mode pilot on 3 to 5 real cameras to get true false-alarm rates.
