"""OpenCV-backed frame sources for real video files and RTSP streams.

Imported lazily by the source factory so that ``import cv2`` (the ``video``
optional dependency) is only required when someone actually points Argus at a
file or a camera. Everything else — tests, the mock backend, CI — never touches
this module.
"""

from __future__ import annotations

from argus.domain import Frame, utcnow
from argus.sources.base import FrameSource, SourceError


def _require_cv2():
    try:
        import cv2  # noqa: PLC0415  (intentional lazy import)

        return cv2
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SourceError(
            "OpenCV is required for file/rtsp sources. Install with: "
            "pip install -r requirements-video.txt"
        ) from exc


class _OpenCvSource(FrameSource):
    """Shared decode/encode logic for file and RTSP sources."""

    def __init__(self, uri: str, camera_id: str, *, jpeg_quality: int = 85) -> None:
        self._uri = uri
        self._camera_id = camera_id
        self._jpeg_quality = jpeg_quality
        self._cap = None
        self._cv2 = None

    def open(self) -> None:
        cv2 = self._cv2 = _require_cv2()
        self._cap = cv2.VideoCapture(self._uri)
        if not self._cap.isOpened():
            raise SourceError(f"could not open source: {self._uri!r}")

    def _grab(self):
        if self._cap is None:
            raise SourceError("read() before open()")
        ok, frame = self._cap.read()
        return ok, frame

    def _encode(self, frame) -> Frame:
        cv2 = self._cv2
        height, width = frame.shape[:2]
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality])
        if not ok:
            raise SourceError("JPEG encode failed")
        return Frame(
            image_bytes=buf.tobytes(),
            media_type="image/jpeg",
            width=int(width),
            height=int(height),
            camera_id=self._camera_id,
            captured_at=utcnow(),
        )

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class FileVideoSource(_OpenCvSource):
    """Reads a finite video file frame-by-frame; returns ``None`` at EOF.

    v0 keeps this simple: the Sampler drives the k-second cadence and this source
    yields the next decoded frame each call. (Wall-clock-accurate replay of a
    file is a Phase-2 nicety, not needed to validate the loop.)
    """

    def read(self) -> Frame | None:
        ok, frame = self._grab()
        if not ok:
            return None  # end of file
        return self._encode(frame)


class RtspSource(_OpenCvSource):
    """Reads the current frame from a live RTSP stream.

    A momentary read failure returns ``None`` (a hiccup) rather than raising —
    the Sampler's reconnect/backoff loop decides when a stream is truly dead.
    """

    def read(self) -> Frame | None:
        ok, frame = self._grab()
        if not ok:
            return None
        return self._encode(frame)
