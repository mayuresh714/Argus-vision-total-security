"""Alerting layer.

    Notifier            - Strategy interface: one way to deliver an alert
    ConsoleNotifier / FileNotifier / WebhookNotifier
    AlertManager        - builds an Alert from an Event, persists evidence,
                          fans out to notifiers, records the alert.
"""

from argus.alerting.manager import AlertManager
from argus.alerting.notifiers import (
    ConsoleNotifier,
    FileNotifier,
    Notifier,
    WebhookNotifier,
)

__all__ = [
    "AlertManager",
    "Notifier",
    "ConsoleNotifier",
    "FileNotifier",
    "WebhookNotifier",
]
