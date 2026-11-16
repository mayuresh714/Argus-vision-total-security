"""Video reading and sliding-window sampling."""
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Window:
    start_s: float
    end_s: float
    frames: np.ndarray  # (T, H, W, 3) RGB uint8


def video_duration(path):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return n / fps


def iter_windows(path, num_frames=16, sample_fps=4.0, stride_s=2.0, size=224):
    """Yield sliding windows of `num_frames` frames sampled at `sample_fps`."""
    cap = cv2.VideoCapture(str(path))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, round(src_fps / sample_fps))
    frames, times, i = [], [], 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if i % step == 0:
            rgb = cv2.cvtColor(cv2.resize(bgr, (size, size)), cv2.COLOR_BGR2RGB)
            frames.append(rgb)
            times.append(i / src_fps)
        i += 1
    cap.release()
    stride = max(1, round(stride_s * sample_fps))
    for s in range(0, len(frames) - num_frames + 1, stride):
        chunk = np.stack(frames[s : s + num_frames])
        yield Window(times[s], times[s + num_frames - 1], chunk)
