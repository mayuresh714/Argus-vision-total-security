"""Argus — single-camera CCTV suspicious-activity detection service (v0).

The package is organised in layers, each depending only on the layer(s) below
it through abstract interfaces (Dependency Inversion):

    api            -> HTTP surface (FastAPI), reads from storage, controls service
    pipeline       -> Sampler + InferenceWorker + Service (composition root)
    decision       -> DecisionEngine (threshold / hysteresis / cooldown)
    vlm            -> VlmBackend implementations + prompt + parser
    alerting       -> AlertManager + Notifier implementations
    sources        -> FrameSource implementations (file / RTSP / fake)
    storage        -> Event/Alert repositories (in-memory / SQLite)
    domain         -> pure data models shared by everything

The core (everything except `sources.file`/`sources.rtsp` and `api`) has no
heavy third-party imports, so it stays testable and edge-deployable.
"""

__version__ = "0.1.0"
