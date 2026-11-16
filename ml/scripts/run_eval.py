import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_ml.encoders import get_encoder
from argus_ml.evaluate import run_eval
from argus_ml.manifest import load_manifest
from argus_ml.report import save_report

ap = argparse.ArgumentParser()
ap.add_argument("--manifest", required=True)
ap.add_argument("--encoder", default="standin", choices=["standin", "vjepa2"])
ap.add_argument("--model", default=None, help="HF model id for vjepa2")
ap.add_argument("--protocol", default="global", choices=["global", "per-site"])
ap.add_argument("--out", default="reports/latest")
ap.add_argument("--cache", default="cache")
ap.add_argument("--num-frames", type=int, default=16)
ap.add_argument("--sample-fps", type=float, default=4.0)
ap.add_argument("--stride-s", type=float, default=2.0)
ap.add_argument("--k", type=int, default=5)
a = ap.parse_args()

enc = get_encoder(a.encoder, model=a.model)
rep = run_eval(load_manifest(a.manifest), enc, a.cache, a.protocol, k=a.k,
               num_frames=a.num_frames, sample_fps=a.sample_fps, stride_s=a.stride_s)
out = save_report(rep, a.out)
print(json.dumps(rep, indent=2)); print("saved to", out)
