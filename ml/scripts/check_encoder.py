"""Sanity-check the real V-JEPA 2 encoder on your machine before a full run."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_ml.encoders import get_encoder

enc = get_encoder("vjepa2", model=sys.argv[1] if len(sys.argv) > 1 else None)
x = np.random.randint(0, 255, (16, 224, 224, 3), dtype=np.uint8)
v = enc.encode(x)
print("embedding shape", v.shape, "finite", bool(np.isfinite(v).all()))
