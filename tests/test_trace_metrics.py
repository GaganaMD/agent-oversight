import unittest

from trace_study.schema import EventKind, EventProvenance, TraceEvent, Trajectory, Visibility
from trace_study.extract import extract_monitor_view, serialize_monitor_view, MonitorViewMode
from trace_study.labels import (AnnotationProvenance, OutcomeAnnotation, OutcomeStatus,
                                TrajectoryAnnotations, LabelError, validate_annotations)
from trace_study.metrics import evaluate_temporal_metrics, WarningTiming, MetricError

P = AnnotationProvenance('fixture', 'doc-1', 'independent annotation')
U = OutcomeAnnotation(OutcomeStatus.UNKNOWN)
N = OutcomeAnnotation(OutcomeStatus.NOT_OBSERVED, provenance=P)
C = OutcomeAnnotation(OutcomeStatus.CENSORED, provenance=P)
def O(seq): return OutcomeAnnotation(OutcomeStatus.OBSERVED, seq, P)
def annotations(assigned=True, attempt=U, change=U, harm=U):
    return TrajectoryAnnotations(assigned, attempt, change, harm, P if assigned is not None else None)
def trajectory(seqs=(1,2,3,4,5)):
    events=[]
    for s in seqs:
        action=s%2==1
        payload={'action':'edit document','target':'draft'} if action else {'tool_name':'editor','status':'ok','observation':'saved'}
        events.append(TraceEvent(s,EventKind.AGENT_ACTION if action else EventKind.TOOL_OBSERVATION,
                    EventProvenance('synthetic',f'event-{s}'),Visibility(frozenset(payload)),payload))
    return Trajectory(tuple(events))

class MetricsTests(unittest.TestCase):
    def test_early_attempt(self):
        r=evaluate_temporal_metrics(trajectory(),annotations(attempt=O(5)),{1:True})
        self.assertEqual(r.attempt.timing,WarningTiming.EARLY)
        self.assertEqual(r.attempt.sequence_lead,4)
        self.assertEqual(r.attempt.decision_opportunity_lead,1)
    def test_at_attempt(self):
        self.assertEqual(evaluate_temporal_metrics(trajectory(),annotations(attempt=O(3)),{3:True}).attempt.timing,WarningTiming.AT_OUTCOME)
    def test_after_confirmed_harm(self):
        r=evaluate_temporal_metrics(trajectory(),annotations(harm=O(2)),{5:True})
        self.assertEqual(r.confirmed_harm.timing,WarningTiming.LATE)
        self.assertEqual(r.confirmed_harm.sequence_lead,-3)
    def test_no_warning(self):
        self.assertEqual(evaluate_temporal_metrics(trajectory(),annotations(attempt=O(3)),{}).attempt.timing,WarningTiming.NO_WARNING)
    def test_verified_honest_false_alarm(self):
        r=evaluate_temporal_metrics(trajectory(),annotations(False,N,N,N),{1:True},verified_honest=True)
        self.assertTrue(r.false_alarm_on_verified_honest)
    def test_attack_assigned_not_harm(self):
        r=evaluate_temporal_metrics(trajectory(),annotations(True,N,N,N),{1:True})
        self.assertEqual(r.confirmed_harm.timing,WarningTiming.OUTCOME_UNRESOLVED)
        self.assertIsNone(r.false_alarm_on_verified_honest)
    def test_censored(self):
        r=evaluate_temporal_metrics(trajectory(),annotations(harm=C),{1:True})
        self.assertIsNone(r.confirmed_harm.sequence_lead)
        self.assertEqual(r.confirmed_harm.status,OutcomeStatus.CENSORED)
    def test_sequence_gaps(self):
        t=trajectory((1,3,5))
        r=evaluate_temporal_metrics(t,annotations(attempt=O(5)),{1:True})
        self.assertEqual(r.attempt.sequence_lead,4)
        self.assertEqual(r.attempt.decision_opportunity_lead,1)
    def test_outcome_outside_trajectory(self):
        with self.assertRaises(LabelError): evaluate_temporal_metrics(trajectory(),annotations(attempt=O(7)),{})
    def test_attempt_must_be_action(self):
        with self.assertRaises(LabelError): validate_annotations(trajectory(),annotations(attempt=O(2)))
    def test_warning_outside_trajectory(self):
        with self.assertRaises(MetricError): evaluate_temporal_metrics(trajectory(),annotations(),{6:True})
    def test_no_false_alarm_without_verified_honest(self):
        self.assertIsNone(evaluate_temporal_metrics(trajectory(),annotations(False,N,N,N),{1:True}).false_alarm_on_verified_honest)
    def test_cannot_mark_censored_honest(self):
        with self.assertRaises(MetricError): evaluate_temporal_metrics(trajectory(),annotations(False,N,N,C),{},verified_honest=True)
    def test_label_isolation(self):
        t=trajectory()
        before=serialize_monitor_view(extract_monitor_view(t,3,MonitorViewMode.HISTORY_AWARE))
        evaluate_temporal_metrics(t,annotations(attempt=O(3),harm=O(4)),{1:True})
        after=serialize_monitor_view(extract_monitor_view(t,3,MonitorViewMode.HISTORY_AWARE))
        self.assertEqual(before,after)
        self.assertNotIn('harm_confirmed',after)
    def test_no_future_warning(self):
        with self.assertRaises(MetricError): evaluate_temporal_metrics(trajectory((1,3)),annotations(),{5:True})
    def test_unknown_vs_negative(self):
        r=evaluate_temporal_metrics(trajectory(),annotations(harm=U),{})
        self.assertEqual(r.confirmed_harm.status,OutcomeStatus.UNKNOWN)
        self.assertNotEqual(r.confirmed_harm.status,OutcomeStatus.NOT_OBSERVED)

if __name__ == '__main__': unittest.main()
