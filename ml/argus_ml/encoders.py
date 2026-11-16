"""Video encoders. All return one embedding vector per window."""
import numpy as np


class StandInEncoder:
    """Tiny motion/appearance feature extractor. NO deep model: only used to
    test the pipeline end to end where no GPU or weights are available.
    Results from it say nothing about V-JEPA."""

    name = "standin"

    def encode(self, frames):
        g = frames.astype(np.float32).mean(axis=3) / 255.0  # (T,H,W)
        t, h, w = g.shape
        diff = np.abs(np.diff(g, axis=0))  # (T-1,H,W)

        def grid(x, n=4):
            x = x[..., : (x.shape[-2] // n) * n, : (x.shape[-1] // n) * n]
            *lead, hh, ww = x.shape
            x = x.reshape(*lead, n, hh // n, n, ww // n)
            return x.mean(axis=(-3, -1))

        motion = grid(diff).mean(axis=0).ravel()  # 16
        motion_peak = grid(diff).max(axis=0).ravel()  # 16
        appearance = grid(g).mean(axis=0).ravel()  # 16
        color = frames.reshape(-1, 3).mean(axis=0) / 255.0
        return np.concatenate([motion * 20, motion_peak * 5, appearance, color]).astype(np.float32)


class VJEPA2Encoder:
    """Frozen V-JEPA 2 via Hugging Face transformers (needs torch + GPU ideally).
    Mean-pools the encoder's patch tokens into a single vector per window.
    Untested in the authoring sandbox (no GPU / weights reachable): verify on
    your machine with `scripts/check_encoder.py`."""

    def __init__(self, model_name="facebook/vjepa2-vitl-fpc64-256", device=None):
        import torch
        from transformers import AutoModel, AutoVideoProcessor

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.name = model_name
        self.processor = AutoVideoProcessor.from_pretrained(model_name)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = AutoModel.from_pretrained(model_name, torch_dtype=dtype).to(self.device).eval()

    def encode(self, frames):
        torch = self.torch
        inputs = self.processor(list(frames), return_tensors="pt").to(self.device)
        if self.device == "cuda":
            inputs = {k: v.half() if v.is_floating_point() else v for k, v in inputs.items()}
        with torch.no_grad():
            feats = self.model.get_vision_features(**inputs)  # (1, tokens, D)
        return feats.float().mean(dim=1)[0].cpu().numpy()


def get_encoder(name, **kw):
    if name == "standin":
        return StandInEncoder()
    if name.startswith("vjepa2"):
        model = kw.get("model") or "facebook/vjepa2-vitl-fpc64-256"
        return VJEPA2Encoder(model)
    raise ValueError(f"unknown encoder {name}")
