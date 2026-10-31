"""Allowlist-based monitor view extraction for offline TRACE trajectories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterator, Mapping

from .schema import EventKind, SchemaError, TraceEvent, Trajectory


class ExtractionError(ValueError):
    """Raised when a requested monitor view cannot be constructed safely."""


class MonitorViewMode(str, Enum):
    ACTION_ONLY = "action_only"
    HISTORY_AWARE = "history_aware"


def _visible_fields_for(kind: EventKind) -> frozenset[str]:
    if kind is EventKind.AGENT_ACTION:
        return frozenset({"action", "target"})
    return frozenset({"tool_name", "status", "observation"})


@dataclass(frozen=True)
class MonitorView:
    """Validated immutable records produced by the monitor-view extractor."""

    records: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple):
            raise ExtractionError("monitor-view records must be a tuple")
        frozen_records: list[Mapping[str, Any]] = []
        for record in self.records:
            if not isinstance(record, Mapping) or set(record) != {"sequence", "kind", "payload"}:
                raise ExtractionError("monitor-view records have an invalid schema")
            sequence, kind, payload = record["sequence"], record["kind"], record["payload"]
            if type(sequence) is not int or sequence < 1:
                raise ExtractionError("monitor-view sequence must be a positive integer")
            try:
                event_kind = EventKind(kind)
            except (TypeError, ValueError) as error:
                raise ExtractionError("monitor-view kind is invalid") from error
            if not isinstance(payload, Mapping) or not set(payload).issubset(_visible_fields_for(event_kind)):
                raise ExtractionError("monitor-view payload is invalid")
            if not all(isinstance(name, str) and isinstance(value, str) for name, value in payload.items()):
                raise ExtractionError("monitor-view payload values must be strings")
            frozen_records.append(
                MappingProxyType(
                    {
                        "sequence": sequence,
                        "kind": event_kind.value,
                        "payload": MappingProxyType({name: payload[name] for name in sorted(payload)}),
                    }
                )
            )
        object.__setattr__(self, "records", tuple(frozen_records))

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        return iter(self.records)

    def __len__(self) -> int:
        return len(self.records)


def _project_event(event: TraceEvent) -> Mapping[str, Any]:
    """Project only structural fields and fields explicitly allowed for this event."""
    return {
        "sequence": event.sequence,
        "kind": event.kind.value,
        "payload": {name: event.payload[name] for name in sorted(event.visibility.monitor_fields)},
    }


def extract_monitor_view(
    trajectory: Trajectory, prefix_sequence: int, mode: MonitorViewMode
) -> MonitorView:
    """Return a monitor-safe, inclusive prefix view.

    ``ACTION_ONLY`` retains agent actions. ``HISTORY_AWARE`` retains both action
    and tool-observation events. Evaluation labels, provenance, private data,
    and unpermitted payload fields have no extraction path.
    """
    if not isinstance(trajectory, Trajectory):
        raise ExtractionError("trajectory must be a Trajectory")
    if type(prefix_sequence) is not int or prefix_sequence < 1:
        raise ExtractionError("prefix_sequence must be a positive integer")
    if not isinstance(mode, MonitorViewMode):
        raise ExtractionError("mode must be a MonitorViewMode")

    included_kinds = (
        {EventKind.AGENT_ACTION}
        if mode is MonitorViewMode.ACTION_ONLY
        else {EventKind.AGENT_ACTION, EventKind.TOOL_OBSERVATION}
    )
    try:
        return MonitorView(
            tuple(
                _project_event(event)
                for event in trajectory.events
                if event.sequence <= prefix_sequence and event.kind in included_kinds
            )
        )
    except SchemaError as error:
        raise ExtractionError("trajectory contained an invalid event") from error


def serialize_monitor_view(view: MonitorView) -> str:
    """Serialize a previously projected view in stable, compact JSON."""
    if not isinstance(view, MonitorView):
        raise ExtractionError("view must be a MonitorView returned by extract_monitor_view")
    try:
        return json.dumps(
            [
                {"sequence": record["sequence"], "kind": record["kind"], "payload": dict(record["payload"])}
                for record in view.records
            ],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ExtractionError("view is not safely JSON-serializable") from error
