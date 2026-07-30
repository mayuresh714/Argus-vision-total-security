"""Typed configuration loaded from YAML (or a dict).

Every tunable knob from docs/01 §4.7 lives here — ``k``, thresholds, cooldown,
model/backend, notifiers, storage, retention — so behaviour changes are config,
not code. Uses stdlib dataclasses (+ optional PyYAML) so the core has no heavy
config-framework dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any


class ConfigError(ValueError):
    """Raised when configuration is structurally invalid."""


@dataclass(frozen=True)
class CameraConfig:
    id: str = "cam-01"
    # Default to "fake" so a bare ``AppConfig()`` is valid and runnable as a demo
    # with no camera; real deployments set file/rtsp + uri via config.
    source: str = "fake"  # "file" | "rtsp" | "fake"
    uri: str = ""  # path or rtsp url; ignored for fake
    sample_interval_seconds: float = 5.0  # this is "k"

    def validate(self) -> None:
        if self.sample_interval_seconds <= 0:
            raise ConfigError("camera.sample_interval_seconds must be > 0")
        if self.source not in {"file", "rtsp", "fake"}:
            raise ConfigError(f"camera.source must be file|rtsp|fake, got {self.source!r}")
        if self.source in {"file", "rtsp"} and not self.uri:
            raise ConfigError(f"camera.uri required for source={self.source}")


@dataclass(frozen=True)
class VlmConfig:
    backend: str = "mock"  # "mock" | "openai_compatible"
    model: str = "qwen3-vl-8b-instruct"
    endpoint: str = "http://localhost:8000/v1/chat/completions"
    api_key_env: str = "ARGUS_VLM_API_KEY"  # env var name, never the key itself
    timeout_seconds: float = 20.0
    max_image_long_side: int = 1024

    def validate(self) -> None:
        if self.backend not in {"mock", "openai_compatible"}:
            raise ConfigError(f"vlm.backend must be mock|openai_compatible, got {self.backend!r}")
        if self.timeout_seconds <= 0:
            raise ConfigError("vlm.timeout_seconds must be > 0")


@dataclass(frozen=True)
class DecisionConfig:
    alert_threshold: float = 0.70
    clear_threshold: float = 0.40  # hysteresis: score must fall below this to "clear"
    cooldown_seconds: float = 60.0
    consecutive_n: int = 1  # require N consecutive over-threshold samples to alert
    review_threshold: float = 0.40
    notify_threshold: float = 0.70
    urgent_threshold: float = 0.90

    def validate(self) -> None:
        for name in (
            "alert_threshold",
            "clear_threshold",
            "review_threshold",
            "notify_threshold",
            "urgent_threshold",
        ):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ConfigError(f"decision.{name} must be in [0,1], got {v}")
        if self.clear_threshold > self.alert_threshold:
            raise ConfigError("decision.clear_threshold must be <= alert_threshold")
        if self.consecutive_n < 1:
            raise ConfigError("decision.consecutive_n must be >= 1")
        if self.cooldown_seconds < 0:
            raise ConfigError("decision.cooldown_seconds must be >= 0")


@dataclass(frozen=True)
class NotifierConfig:
    type: str  # "console" | "file" | "webhook"
    options: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.type not in {"console", "file", "webhook"}:
            raise ConfigError(f"notifier.type must be console|file|webhook, got {self.type!r}")
        if self.type == "webhook" and not self.options.get("url"):
            raise ConfigError("webhook notifier requires options.url")
        if self.type == "file" and not self.options.get("path"):
            raise ConfigError("file notifier requires options.path")


@dataclass(frozen=True)
class StorageConfig:
    backend: str = "memory"  # "memory" | "sqlite"
    path: str = "argus.db"  # sqlite file
    evidence_dir: str = "evidence"
    retention_days: int = 7

    def validate(self) -> None:
        if self.backend not in {"memory", "sqlite"}:
            raise ConfigError(f"storage.backend must be memory|sqlite, got {self.backend!r}")
        if self.retention_days < 0:
            raise ConfigError("storage.retention_days must be >= 0")


@dataclass(frozen=True)
class ApiConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    vlm: VlmConfig = field(default_factory=VlmConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    notifiers: tuple[NotifierConfig, ...] = field(
        default_factory=lambda: (NotifierConfig(type="console"),)
    )
    storage: StorageConfig = field(default_factory=StorageConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    log_level: str = "INFO"

    def validate(self) -> "AppConfig":
        self.camera.validate()
        self.vlm.validate()
        self.decision.validate()
        self.storage.validate()
        for n in self.notifiers:
            n.validate()
        return self

    # ---- loading -------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        data = data or {}
        cfg = cls(
            camera=_build(CameraConfig, data.get("camera")),
            vlm=_build(VlmConfig, data.get("vlm")),
            decision=_build(DecisionConfig, data.get("decision")),
            notifiers=tuple(
                _build(NotifierConfig, n) for n in (data.get("notifiers") or [{"type": "console"}])
            ),
            storage=_build(StorageConfig, data.get("storage")),
            api=_build(ApiConfig, data.get("api")),
            log_level=str(data.get("log_level", "INFO")),
        )
        return cfg.validate()

    @classmethod
    def from_yaml(cls, path: str) -> "AppConfig":
        import yaml  # local import: only needed for file-based config

        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh) or {})


def _build(dc_type: type, data: Any):
    """Construct a (frozen) dataclass from a possibly-partial dict, ignoring
    unknown keys so config files can carry comments/extras without crashing."""
    if data is None:
        return dc_type()
    if not isinstance(data, dict):
        raise ConfigError(f"expected mapping for {dc_type.__name__}, got {type(data).__name__}")
    if not is_dataclass(dc_type):  # pragma: no cover - defensive
        raise ConfigError(f"{dc_type} is not a dataclass")
    allowed = {f.name for f in fields(dc_type)}
    kwargs = {k: v for k, v in data.items() if k in allowed}
    return dc_type(**kwargs)
