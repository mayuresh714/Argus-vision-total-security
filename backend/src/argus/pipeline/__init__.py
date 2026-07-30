"""Pipeline: the moving parts that connect a source to alerts.

    LatestSlot        - a size-1, drop-oldest handoff (freshness over backlog)
    Sampler           - grabs a frame every k seconds onto the slot
    InferenceWorker   - consumes the slot: VLM -> decision -> event/alert
    ArgusService      - composition root; wires everything and runs the threads
    build_service     - factory that constructs a service from AppConfig
"""

from argus.pipeline.latest_slot import LatestSlot
from argus.pipeline.sampler import Sampler
from argus.pipeline.service import ArgusService, build_service
from argus.pipeline.worker import InferenceWorker

__all__ = ["LatestSlot", "Sampler", "InferenceWorker", "ArgusService", "build_service"]
