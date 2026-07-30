"""Decision layer: turns a raw suspicion score into an alert-or-not decision."""

from argus.decision.engine import Decision, DecisionEngine

__all__ = ["Decision", "DecisionEngine"]
