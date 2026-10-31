"""Independent, evaluation-only TRACE outcome annotations.

Annotations are deliberately not part of the monitor-view API. Missing outcome
information is never treated as a verified negative outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .schema import Trajectory


class LabelError(ValueError):
    """Invalid independent annotation or incompatible trajectory."""


class OutcomeStatus(str, Enum):
    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"  # checked throughout a complete observation window
    UNKNOWN = "unknown"            # not checked or insufficient evidence
    CENSORED = "censored"          # observation ended before outcome could be ruled out


@dataclass(frozen=True)
class AnnotationProvenance:
    source: str
    source_id: str
    method: str

    def __post_init__(self) -> None:
        for name in ("source", "source_id", "method"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise LabelError(f"annotation provenance {name} must be nonempty")


@dataclass(frozen=True)
class OutcomeAnnotation:
    status: OutcomeStatus
    first_sequence: int | None = None
    provenance: AnnotationProvenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, OutcomeStatus):
            raise LabelError("status must be OutcomeStatus")
        if self.status is OutcomeStatus.OBSERVED:
            if type(self.first_sequence) is not int or self.first_sequence < 1:
                raise LabelError("observed outcomes require a positive first_sequence")
            if not isinstance(self.provenance, AnnotationProvenance):
                raise LabelError("observed outcomes require independent provenance")
        elif self.first_sequence is not None:
            raise LabelError("unobserved/unknown/censored outcomes cannot have first_sequence")
        if self.provenance is not None and not isinstance(self.provenance, AnnotationProvenance):
            raise LabelError("invalid provenance")


@dataclass(frozen=True)
class TrajectoryAnnotations:
    """Evaluation-only labels, never passed into extraction or monitor scoring.

    attack_assigned=None means assignment metadata is unavailable. An assignment
    is not evidence of intention, an attempted violation, or confirmed harm.
    """
    attack_assigned: bool | None
    attempt: OutcomeAnnotation
    state_change: OutcomeAnnotation
    confirmed_harm: OutcomeAnnotation
    assignment_provenance: AnnotationProvenance | None = None

    def __post_init__(self) -> None:
        if self.attack_assigned is not None and type(self.attack_assigned) is not bool:
            raise LabelError("attack_assigned must be bool or None")
        if self.attack_assigned is not None and not isinstance(self.assignment_provenance, AnnotationProvenance):
            raise LabelError("known assignment requires provenance")
        if self.assignment_provenance is not None and not isinstance(self.assignment_provenance, AnnotationProvenance):
            raise LabelError("invalid assignment provenance")
        for name in ("attempt", "state_change", "confirmed_harm"):
            if not isinstance(getattr(self, name), OutcomeAnnotation):
                raise LabelError(f"{name} must be OutcomeAnnotation")


def validate_annotations(trajectory: Trajectory, annotations: TrajectoryAnnotations) -> None:
    """Check that observed outcomes correspond to recorded, action-capable steps.

    A state change or confirmed harm can be recorded on a tool-observation step;
    an attempted action must be anchored to an agent-action step. No causal or
    monotonic ordering between labels is assumed without independent evidence.
    """
    from .schema import EventKind
    if not isinstance(trajectory, Trajectory) or not isinstance(annotations, TrajectoryAnnotations):
        raise LabelError("expected Trajectory and TrajectoryAnnotations")
    by_seq = {event.sequence: event for event in trajectory.events}
    for name in ("attempt", "state_change", "confirmed_harm"):
        annotation = getattr(annotations, name)
        if annotation.status is OutcomeStatus.OBSERVED:
            if annotation.first_sequence not in by_seq:
                raise LabelError(f"{name} first_sequence is not a recorded event")
            if name == "attempt" and by_seq[annotation.first_sequence].kind is not EventKind.AGENT_ACTION:
                raise LabelError("attempt must be anchored to an agent action")
