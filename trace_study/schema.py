"""Typed, validation-first records for offline TRACE trajectories.

Events hold only monitor-candidate payload fields.  Information that must never
reach a monitor belongs in ``private_data``; evaluation outcomes belong in the
separate ``EvaluationLabels`` record.  Neither is used by view extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias


JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class SchemaError(ValueError):
    """Raised when a trajectory record is malformed or ambiguously specified."""


class EventKind(str, Enum):
    AGENT_ACTION = "agent_action"
    TOOL_OBSERVATION = "tool_observation"


# These are positive allowlists, not names to remove from a raw event. Version
# 1 permits only scalar monitor fields; typed nested arguments can be added by
# a separately specified future schema.
MONITOR_PAYLOAD_ALLOWLIST: Mapping[EventKind, frozenset[str]] = MappingProxyType(
    {
        EventKind.AGENT_ACTION: frozenset({"action", "target"}),
        EventKind.TOOL_OBSERVATION: frozenset({"tool_name", "status", "observation"}),
    }
)


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _freeze_json(value: Any) -> JsonValue:
    """Validate, copy, and recursively freeze a finite JSON-compatible value."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SchemaError("JSON numbers must be finite")
        return value
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)  # type: ignore[return-value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise SchemaError("JSON objects must have string keys")
        return MappingProxyType({key: _freeze_json(value[key]) for key in sorted(value)})  # type: ignore[return-value]
    raise SchemaError("value must be JSON-compatible")


def _frozen_mapping(value: Mapping[str, JsonValue], field_name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise SchemaError(f"{field_name} must be a mapping with string keys")
    try:
        return MappingProxyType({key: _freeze_json(value[key]) for key in sorted(value)})
    except SchemaError as error:
        raise SchemaError(f"{field_name} must contain finite JSON-compatible values") from error


@dataclass(frozen=True)
class EventProvenance:
    """Where an event came from, retained for auditing but not monitor exposure."""

    source: str
    source_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise SchemaError("provenance.source must be a non-empty string")
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise SchemaError("provenance.source_id must be a non-empty string")


@dataclass(frozen=True)
class Visibility:
    """Explicit permission for a subset of the event's allowlisted fields."""

    monitor_fields: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.monitor_fields, frozenset) or not all(
            isinstance(name, str) for name in self.monitor_fields
        ):
            raise SchemaError("visibility.monitor_fields must be a frozenset of strings")


@dataclass(frozen=True)
class EvaluationLabels:
    """Evaluation-only outcomes; extractors must never include these in views."""

    attack_assigned: bool = False
    harmful_action_attempted: bool = False
    harmful_state_change: bool = False
    harm_confirmed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "attack_assigned",
            "harmful_action_attempted",
            "harmful_state_change",
            "harm_confirmed",
        ):
            if type(getattr(self, name)) is not bool:
                raise SchemaError(f"evaluation label {name} must be a bool")


@dataclass(frozen=True)
class TraceEvent:
    """One chronological action or tool observation with an explicit view policy."""

    sequence: int
    kind: EventKind
    provenance: EventProvenance
    visibility: Visibility
    payload: Mapping[str, JsonValue]
    timestamp: datetime | None = None
    private_data: Mapping[str, JsonValue] = field(default_factory=dict, repr=False, compare=False)
    evaluation: EvaluationLabels = field(default_factory=EvaluationLabels, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 1:
            raise SchemaError("sequence must be a positive integer")
        if not isinstance(self.kind, EventKind):
            raise SchemaError("kind must be an EventKind")
        if not isinstance(self.provenance, EventProvenance):
            raise SchemaError("provenance must be EventProvenance")
        if not isinstance(self.visibility, Visibility):
            raise SchemaError("visibility must be Visibility")
        if self.timestamp is not None and not isinstance(self.timestamp, datetime):
            raise SchemaError("timestamp must be a datetime or None")
        if not isinstance(self.evaluation, EvaluationLabels):
            raise SchemaError("evaluation must be EvaluationLabels")

        payload = _frozen_mapping(self.payload, "payload")
        private_data = _frozen_mapping(self.private_data, "private_data")
        allowed = MONITOR_PAYLOAD_ALLOWLIST[self.kind]
        if not set(payload).issubset(allowed):
            raise SchemaError("payload contains a field outside the monitor allowlist")
        if not self.visibility.monitor_fields.issubset(set(payload)):
            raise SchemaError("visible fields must be present in payload")
        if not self.visibility.monitor_fields.issubset(allowed):
            raise SchemaError("visible fields must be allowlisted for this event kind")
        if not all(isinstance(value, str) for value in payload.values()):
            raise SchemaError("version-1 monitor payload values must be strings")
        if self.kind is EventKind.AGENT_ACTION and not _non_empty_string(payload.get("action")):
            raise SchemaError("agent actions require a non-empty action field")
        if self.kind is EventKind.TOOL_OBSERVATION:
            if not _non_empty_string(payload.get("tool_name")) or not _non_empty_string(payload.get("status")):
                raise SchemaError("tool observations require non-empty tool_name and status fields")
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "private_data", private_data)


@dataclass(frozen=True)
class Trajectory:
    """A sequence-addressed trajectory, normalized into chronological order.

    Sequence numbers are authoritative. Gaps represent unrecorded events, and
    prefixes include only records at or below the requested sequence. Timestamps
    are audit metadata only and are not used to infer ordering.
    """

    events: tuple[TraceEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.events, tuple) or not self.events:
            raise SchemaError("events must be a non-empty tuple")
        if not all(isinstance(event, TraceEvent) for event in self.events):
            raise SchemaError("events must contain only TraceEvent records")
        sequences = [event.sequence for event in self.events]
        if len(sequences) != len(set(sequences)):
            raise SchemaError("duplicate event sequence numbers are ambiguous")
        object.__setattr__(self, "events", tuple(sorted(self.events, key=lambda event: event.sequence)))
