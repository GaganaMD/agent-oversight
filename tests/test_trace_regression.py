import json
import math
import unittest
from datetime import datetime, timezone
from trace_study import (EventKind, EventProvenance, EvaluationLabels, TraceEvent, Trajectory, Visibility, MonitorView, MonitorViewMode, extract_monitor_view, serialize_monitor_view)
from trace_study.schema import SchemaError
from trace_study.extract import ExtractionError

P = EventProvenance('synthetic','fixture')

def action(seq=1, payload=None, visible=None, **kw):
    payload = {'action':'edit','target':'draft'} if payload is None else payload
    return TraceEvent(seq, EventKind.AGENT_ACTION, P, Visibility(frozenset(payload if visible is None else visible)), payload, **kw)

def observation(seq=2):
    return TraceEvent(seq, EventKind.TOOL_OBSERVATION, P, Visibility(frozenset({'tool_name','status','observation'})), {'tool_name':'editor','status':'ok','observation':'saved'})

class TraceRegressionTests(unittest.TestCase):
    def test_nested_arguments_rejected(self):
        with self.assertRaises(SchemaError):
            action(payload={'action':'edit','arguments':{'private_reasoning':'secret'}})
    def test_nested_private_data_frozen(self):
        original={'nested':{'list':[{'x':1}]}}
        ev=action(private_data=original)
        original['nested']['list'][0]['x']=99
        self.assertEqual(ev.private_data['nested']['list'][0]['x'],1)
        with self.assertRaises(TypeError):
            ev.private_data['nested']['list'][0]['x']=5
    def test_arbitrary_serializer_input_rejected(self):
        with self.assertRaises(ExtractionError):
            serialize_monitor_view(({'harm_confirmed':True},))
        with self.assertRaises(ExtractionError):
            MonitorView(({'sequence':1,'kind':'agent_action','payload':{'harm_confirmed':'true'}},))
    def test_timestamp_and_labels_omitted(self):
        ev=action(timestamp=datetime.now(timezone.utc),evaluation=EvaluationLabels(True,True,True,True),private_data={'hidden':'secret'})
        result=serialize_monitor_view(extract_monitor_view(Trajectory((ev,)),1,MonitorViewMode.HISTORY_AWARE))
        for field in ('timestamp','attack_assigned','harm_confirmed','private_data','secret'):
            self.assertNotIn(field,result)
    def test_nonfinite_nested_private_data_rejected(self):
        for v in (math.nan,math.inf,-math.inf):
            with self.subTest(v=v),self.assertRaises(SchemaError):
                action(private_data={'a':[{'b':v}]})
    def test_blank_required_rejected(self):
        for value in ('','   '):
            with self.subTest(value=value),self.assertRaises(SchemaError):
                action(payload={'action':value})
            with self.subTest(value=value),self.assertRaises(SchemaError):
                TraceEvent(1,EventKind.TOOL_OBSERVATION,P,Visibility(frozenset({'tool_name','status'})),{'tool_name':'editor','status':value})
    def test_sequence_gaps_and_prefix(self):
        tr=Trajectory((observation(7),action(1)))
        self.assertEqual([e.sequence for e in tr.events],[1,7])
        self.assertEqual(len(extract_monitor_view(tr,6,MonitorViewMode.HISTORY_AWARE)),1)
        self.assertEqual(len(extract_monitor_view(tr,7,MonitorViewMode.ACTION_ONLY)),1)
    def test_duplicate_sequence_rejected(self):
        with self.assertRaises(SchemaError):
            Trajectory((action(1),action(1)))
    def test_independent_equivalent_inputs_deterministic(self):
        a=action(payload={'target':'draft','action':'edit'})
        b=action(payload={'action':'edit','target':'draft'})
        left=serialize_monitor_view(extract_monitor_view(Trajectory((a,)),1,MonitorViewMode.ACTION_ONLY))
        right=serialize_monitor_view(extract_monitor_view(Trajectory((b,)),1,MonitorViewMode.ACTION_ONLY))
        self.assertEqual(left,right)
    def test_direct_monitorview_rejects_nested(self):
        with self.assertRaises(ExtractionError):
            MonitorView(({'sequence':1,'kind':'agent_action','payload':{'action':{'private_reasoning':'secret'}}},))
    def test_payload_allowlist_excludes_private_field(self):
        ev=action(payload={'action':'edit','target':'draft'},visible={'action'},private_data={'x':'secret'})
        out=json.loads(serialize_monitor_view(extract_monitor_view(Trajectory((ev,)),1,MonitorViewMode.ACTION_ONLY)))
        self.assertEqual(out[0]['payload'],{'action':'edit'})

if __name__=='__main__': unittest.main()
