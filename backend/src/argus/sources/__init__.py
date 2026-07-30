"""Frame sources: where footage comes from.

``FrameSource`` is the abstraction the sampler depends on. Concrete sources:

    FakeSource            - scripted frames, no deps (tests / demos / CI)
    FileVideoSource       - a video file via OpenCV        (extra: video)
    RtspSource            - a live RTSP stream via OpenCV   (extra: video)

Only the fake source lives in the always-imported core; the OpenCV-backed ones
are imported lazily by the factory so the core stays dependency-light.
"""

from argus.sources.base import FrameSource, SourceError
from argus.sources.fake_source import FakeSource

__all__ = ["FrameSource", "SourceError", "FakeSource"]
