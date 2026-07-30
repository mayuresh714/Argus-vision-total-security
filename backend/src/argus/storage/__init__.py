"""Persistence layer (Repository pattern).

    Repository            - abstract Event + Alert persistence
    InMemoryRepository    - dict-backed, for tests/demos
    SqliteRepository      - zero-ops single-file store for a real single camera

    EvidenceWriter        - persists the evidence image for an alert
    NullEvidenceWriter / FileEvidenceWriter
"""

from argus.storage.base import EvidenceWriter, Repository
from argus.storage.evidence import FileEvidenceWriter, NullEvidenceWriter
from argus.storage.memory_repository import InMemoryRepository
from argus.storage.sqlite_repository import SqliteRepository

__all__ = [
    "Repository",
    "EvidenceWriter",
    "InMemoryRepository",
    "SqliteRepository",
    "FileEvidenceWriter",
    "NullEvidenceWriter",
]
