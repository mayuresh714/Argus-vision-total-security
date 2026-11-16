import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_ml.synthetic import make_dataset
from argus_ml.manifest import write_manifest

ap = argparse.ArgumentParser(); ap.add_argument("--out", default="data/synthetic")
a = ap.parse_args()
rows = make_dataset(a.out)
write_manifest(rows, Path(a.out) / "manifest.csv")
print(f"wrote {len(rows)} videos + manifest to {a.out}")
