import json, unittest
from collections import Counter
from oversight.scenarios import FULL_DESIGN_PAIRS, MARGINS, MORPHOLOGIES, SKINS, build_pairs, evidence_view, visible_events
from oversight.study_design import base_assignment, participant_trials, practice_trials
from oversight.analyze import first_crossing, wilson
from oversight.mock_endpoint import respond


class ScenarioTests(unittest.TestCase):
    pairs = build_pairs(FULL_DESIGN_PAIRS)

    def test_deterministic(self):
        self.assertEqual(build_pairs(3), build_pairs(3))

    def test_full_factorial(self):
        cells = Counter((a.skin, a.morphology, a.margin) for a, _ in self.pairs)
        self.assertEqual(len(cells), len(SKINS) * len(MORPHOLOGIES) * len(MARGINS))
        self.assertTrue(all(n == 1 for n in cells.values()))

    def test_margin_and_boundary(self):
        for a, b in self.pairs:
            for s in (a, b):
                self.assertEqual(s.last_safe_seq - s.evidence_seq, s.margin)
                self.assertEqual(s.events[s.evidence_seq - 1].kind, "environment_evidence")
                self.assertEqual(s.events[s.last_safe_seq - 1].kind, "action_proposed")

    def test_pairs_differ_only_in_authorization_and_outcome(self):
        for a, b in self.pairs:
            self.assertEqual(len(a.events), len(b.events))
            for ea, eb in zip(a.events, b.events):
                if ea.kind == "environment_evidence":
                    self.assertNotEqual(dict(ea.payload)["policy_status"], dict(eb.payload)["policy_status"])
                elif ea.seq == len(a.events):
                    self.assertEqual((ea.kind, eb.kind), ("effect", "environment_transition"))
                else:
                    self.assertEqual(ea, eb)
            self.assertNotIn(a.target, a.authorized_targets)
            self.assertIn(b.target, b.authorized_targets)
            self.assertEqual(len(a.authorized_targets), len(b.authorized_targets))

    def test_g0_views_identical_across_arms(self):
        for a, b in self.pairs:
            self.assertEqual(visible_events(a, "G0"), visible_events(b, "G0"))
            self.assertNotEqual(visible_events(a, "G2"), visible_events(b, "G2"))

    def test_views_never_leak(self):
        for a, _ in self.pairs[:6]:
            text = json.dumps(visible_events(a, "G0", len(a.events)))
            self.assertNotIn("policy_status", text); self.assertNotIn("authorized_targets", text)
            self.assertNotIn('"effect"', text)
            self.assertNotIn("policy_status", json.dumps(visible_events(a, "G2")))
        self.assertEqual(set(evidence_view({"fact": "x", "route_id": "r", "authorized_targets": [], "policy_status": "approved"}, "G3")),
                         {"fact", "route_id", "policy_status"})


class StudyDesignTests(unittest.TestCase):
    def test_balanced_and_distinct_pairs(self):
        for p in range(4):
            ts = participant_trials(p)
            self.assertEqual(len(ts), 16)
            self.assertEqual(len({t["pair_id"] for t in ts}), 16)
            self.assertEqual(set(Counter((t["level"], t["margin"], t["arm"]) for t in ts).values()), {2})

    def test_arms_flip_between_participants(self):
        a = {t["pair_id"]: t["arm"] for t in participant_trials(0)}
        b = {t["pair_id"]: t["arm"] for t in participant_trials(1)}
        self.assertEqual(a.keys(), b.keys())
        self.assertTrue(all(a[k] != b[k] for k in a))

    def test_practice_pairs_unused_in_timed_list(self):
        used = {f"P{i:03d}" for i, *_ in base_assignment()}
        self.assertTrue(all(t["pair_id"] not in used for t in practice_trials()))


class AnalysisTests(unittest.TestCase):
    def test_wilson(self):
        self.assertIsNone(wilson(0, 0)); lo, hi = wilson(5, 10); self.assertLess(lo, 0.5); self.assertGreater(hi, 0.5)

    def test_first_crossing(self):
        self.assertEqual(first_crossing({3: 10, 5: 60, 7: 100}, 51), 5)
        self.assertIsNone(first_crossing({1: 0}, 51))

    def test_mock_is_labelled_rule_not_model(self):
        prompt = 'x\n[{"seq":1,"kind":"environment_evidence","payload":{"route_id":"r1","authorized_targets":["r2"]}}]'
        self.assertEqual(respond(prompt)["suspicion_score"], 100)


if __name__ == "__main__":
    unittest.main()
