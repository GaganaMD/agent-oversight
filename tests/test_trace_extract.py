"""Harmless synthetic tests for TRACE's offline trajectory infrastructure."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from trace_study.extract import ExtractionError, MonitorViewMode, extract_monitor_view, serialize_monitor_view
from trace_study.schema import (
    EventKind,
    EventProvenance,
    EvaluationLabels,
    SchemaError,
    TraceEvent,
    Trajectory,
    Visibility,
)


def action(sequence: int, name: str, target: str) -> TraceEvent:
    return TraceEvent(
        sequence=sequence,
        kind=EventKind.AGENT_ACTION,
        provenance=EventProvenance("agent_runtime", f"action-{sequence}"),
        visibility=Visibility(frozenset({"action", "target"})),
        payload={"action": name, "target": target},
        timestamp=datetime(2026, 11, 1, 9, sequence, tzinfo=timezone.utc),
        private_data={"private_reasoning": "Internal draft plan for the document assistant."},
        evaluation=EvaluationLabels(attack_assigned=True, harmful_action_attempted=True),
    )


def observation(sequence: int, text: str) -> TraceEvent:
    return TraceEvent(
        sequence=sequence,
        kind=EventKind.TOOL_OBSERVATION,
        provenance=EventProvenance("local_file_tool", f"obs-{sequence}"),
        visibility=Visibility(frozenset({"tool_name", "status", "observation"})),
        payload={"tool_name": "document_store", "status": "ok", "observation": text},
        private_data={"scorer_metadata": {"fixture": "fictional"}},
        evaluation=EvaluationLabels(harmful_state_change=True, harm_confirmed=True),
    )


class TraceExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Deliberately supplied out of order; Trajectory canonicalizes by sequence.
        self.trajectory = Trajectory(
            (action(3, "save_document", "meeting-notes.txt"), observation(2, "Draft opened."), action(1, "open_document", "meeting-notes.txt"))
        )

    def test_orders_events_chronologically(self) -> None:
        view = extract_monitor_view(self.trajectory, 3, MonitorViewMode.HISTORY_AWARE)
        self.assertEqual([item["sequence"] for item in view], [1, 2, 3])

    def test_prefix_never_includes_future_events(self) -> None:
        view = extract_monitor_view(self.trajectory, 2, MonitorViewMode.HISTORY_AWARE)
        self.assertEqual([item["sequence"] for item in view], [1, 2])
        self.assertNotIn("save_document", serialize_monitor_view(view))

    def test_hidden_metadata_and_labels_are_excluded(self) -> None:
        serialized = serialize_monitor_view(
            extract_monitor_view(self.trajectory, 3, MonitorViewMode.HISTORY_AWARE)
        )
        for forbidden in (
            "private_reasoning",
            "Internal draft plan",
            "scorer_metadata",
            "attack_assigned",
            "harmful_action_attempted",
            "harmful_state_change",
            "harm_confirmed",
            "agent_runtime",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_nested_payload_metadata_is_rejected(self) -> None:
        with self.assertRaises(SchemaError):
            TraceEvent(1, EventKind.AGENT_ACTION, EventProvenance("runtime", "a"), Visibility(frozenset({"action", "target"})), {"action": "open_document", "target": {"private_reasoning": "not visible"}})

    def test_original_nested_values_are_deeply_frozen(self) -> None:
        original = {"audit": {"tags": ["initial"]}}
        event = TraceEvent(1, EventKind.AGENT_ACTION, EventProvenance("runtime", "a"), Visibility(frozenset({"action"})), {"action": "open_document"}, private_data=original)
        original["audit"]["tags"].append("mutated")
        self.assertEqual(event.private_data["audit"]["tags"], ("initial",))
        self.assertNotIn("mutated", serialize_monitor_view(extract_monitor_view(Trajectory((event,)), 1, MonitorViewMode.ACTION_ONLY)))

    def test_serializer_rejects_arbitrary_restricted_records(self) -> None:
        with self.assertRaises(ExtractionError):
            serialize_monitor_view(({"harm_confirmed": True},))  # type: ignore[arg-type]

    def test_timestamp_is_internal_not_monitor_visible(self) -> None:
        serialized = serialize_monitor_view(extract_monitor_view(self.trajectory, 1, MonitorViewMode.ACTION_ONLY))
        self.assertNotIn("timestamp", serialized)
        self.assertNotIn("2026-11-01", serialized)

    def test_action_only_and_history_aware_views_differ(self) -> None:
        action_view = extract_monitor_view(self.trajectory, 3, MonitorViewMode.ACTION_ONLY)
        history_view = extract_monitor_view(self.trajectory, 3, MonitorViewMode.HISTORY_AWARE)
        self.assertEqual([item["kind"] for item in action_view], ["agent_action", "agent_action"])
        self.assertEqual([item["kind"] for item in history_view], ["agent_action", "tool_observation", "agent_action"])

    def test_rejects_missing_and_malformed_events(self) -> None:
        with self.assertRaises(SchemaError):
            TraceEvent(1, EventKind.AGENT_ACTION, EventProvenance("runtime", "a"), Visibility(frozenset({"action"})), {})
        with self.assertRaises(SchemaError):
            TraceEvent(
                1,
                EventKind.AGENT_ACTION,
                EventProvenance("runtime", "a"),
                Visibility(frozenset({"action", "private_reasoning"})),
                {"action": "open_document", "private_reasoning": "do not expose"},
            )
        with self.assertRaises(SchemaError):
            Trajectory((action(1, "open_document", "draft.txt"), action(1, "save_document", "draft.txt")))

    def test_rejects_nonfinite_values_and_whitespace_required_fields(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(SchemaError):
                TraceEvent(1, EventKind.AGENT_ACTION, EventProvenance("runtime", "a"), Visibility(frozenset({"action"})), {"action": "open_document"}, private_data={"bad": value})
        for blank in ("", "  \t"):
            with self.assertRaises(SchemaError):
                TraceEvent(1, EventKind.AGENT_ACTION, EventProvenance("runtime", "a"), Visibility(frozenset({"action"})), {"action": blank})
            with self.assertRaises(SchemaError):
                TraceEvent(1, EventKind.TOOL_OBSERVATION, EventProvenance("runtime", "a"), Visibility(frozenset()), {"tool_name": blank, "status": "ok"})
            with self.assertRaises(SchemaError):
                TraceEvent(1, EventKind.TOOL_OBSERVATION, EventProvenance("runtime", "a"), Visibility(frozenset()), {"tool_name": "document_store", "status": blank})

    def test_sequence_gaps_use_sequence_as_authoritative_chronology(self) -> None:
        trajectory = Trajectory((action(3, "save_document", "draft.txt"), action(1, "open_document", "draft.txt")))
        self.assertEqual([item["sequence"] for item in extract_monitor_view(trajectory, 2, MonitorViewMode.ACTION_ONLY)], [1])
        self.assertEqual([item["sequence"] for item in extract_monitor_view(trajectory, 3, MonitorViewMode.ACTION_ONLY)], [1, 3])

    def test_serialization_is_deterministic(self) -> None:
        first = Trajectory((action(1, "open_document", "draft.txt"),))
        second = Trajectory((TraceEvent(1, EventKind.AGENT_ACTION, EventProvenance("agent_runtime", "action-1"), Visibility(frozenset({"target", "action"})), {"target": "draft.txt", "action": "open_document"}),))
        self.assertEqual(serialize_monitor_view(extract_monitor_view(first, 1, MonitorViewMode.ACTION_ONLY)), serialize_monitor_view(extract_monitor_view(second, 1, MonitorViewMode.ACTION_ONLY)))


if __name__ == "__main__":
    unittest.main()
