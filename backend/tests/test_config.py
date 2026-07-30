import pytest

from argus.config import AppConfig, ConfigError


def test_defaults_are_valid():
    cfg = AppConfig()
    assert cfg.validate() is cfg
    assert cfg.camera.sample_interval_seconds == 5.0
    assert cfg.vlm.backend == "mock"


def test_from_dict_partial_overrides_and_ignores_unknown_keys():
    cfg = AppConfig.from_dict(
        {
            "camera": {"id": "front", "source": "fake", "sample_interval_seconds": 2},
            "decision": {"alert_threshold": 0.8},
            "unknown_top": {"x": 1},  # ignored
            "vlm": {"backend": "mock", "bogus": True},  # bogus ignored
        }
    )
    assert cfg.camera.id == "front"
    assert cfg.camera.sample_interval_seconds == 2
    assert cfg.decision.alert_threshold == 0.8


def test_invalid_interval_rejected():
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"camera": {"source": "fake", "sample_interval_seconds": 0}})


def test_clear_threshold_above_alert_rejected():
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"decision": {"alert_threshold": 0.5, "clear_threshold": 0.9}})


def test_file_source_requires_uri():
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"camera": {"source": "file", "uri": ""}})


def test_webhook_notifier_requires_url():
    with pytest.raises(ConfigError):
        AppConfig.from_dict({"notifiers": [{"type": "webhook", "options": {}}]})


def test_notifiers_parsed():
    cfg = AppConfig.from_dict(
        {
            "camera": {"source": "fake"},
            "notifiers": [
                {"type": "console"},
                {"type": "file", "options": {"path": "a.jsonl"}},
            ],
        }
    )
    assert [n.type for n in cfg.notifiers] == ["console", "file"]
