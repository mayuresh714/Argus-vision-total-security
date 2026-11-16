import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_ml.ucf_crime import build
from argus_ml.manifest import write_manifest

ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True, help="folder containing the downloaded UCF-Crime videos")
ap.add_argument("--temporal", help="optional temporal annotation .txt for test videos")
ap.add_argument("--out", default="data/ucf_manifest.csv")
a = ap.parse_args()
rows = build(a.root, a.temporal)
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
write_manifest(rows, a.out)
from collections import Counter
print(Counter(r.label for r in rows)); print("wrote", a.out)
