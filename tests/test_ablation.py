import unittest
from oversight.ablation.analyze_ablation import auc, holm, mcnemar_exact
from oversight.ablation.prompts import BASE, CELLS, OVERSEER, RULE_W2, cell_template
from oversight.ablation.run_ablation import plan


def changed_lines(a: str, b: str) -> tuple[set, set]:
    la, lb = set(a.splitlines()), set(b.splitlines())
    return la - lb, lb - la


class PromptCellTests(unittest.TestCase):
    def test_w0_score_is_the_frozen_prompt(self):
        self.assertEqual(cell_template("W0-S"), BASE)
        self.assertEqual(cell_template("R"), OVERSEER)

    def test_w1_only_deletes_the_two_clauses(self):
        removed, added = changed_lines(cell_template("W0-S"), cell_template("W1-S"))
        self.assertEqual(len(removed), 2); self.assertEqual(len(added), 2)
        self.assertTrue(any("route policy" in l for l in removed))
        self.assertTrue(any("route identifiers" in l for l in removed))
        self.assertFalse(any("route" in l for l in added))

    def test_w2_adds_exactly_one_rule(self):
        removed, added = changed_lines(cell_template("W1-S"), cell_template("W2-S"))
        self.assertEqual(removed, set()); self.assertEqual(added, {RULE_W2.strip()})

    def test_format_change_leaves_rules_alone(self):
        for w in ("W0", "W1", "W2"):
            s, d = cell_template(f"{w}-S"), cell_template(f"{w}-D")
            self.assertEqual(s.split("JSON schema:")[0], d.split("JSON schema:")[0])
            self.assertIn('"decision": "revoke" | "allow"', d)
            self.assertNotIn("consequence", d.lower()); self.assertNotIn("legitimate task", d.lower())

    def test_every_template_has_the_events_slot(self):
        for c in CELLS: self.assertIn("{VISIBLE_EVENTS_JSON}", cell_template(c))


class PlanTests(unittest.TestCase):
    def test_plan_size(self):
        jobs = plan()
        per_cell = {c: sum(1 for j in jobs if j[3]["cell"] == c) for c in CELLS}
        # 323 unique temperature-0 inputs (one clean prefix is shared by P002 and P038) + 5 x 216 samples
        self.assertEqual(set(per_cell.values()), {323 + 5 * 216})
        self.assertTrue(all(j[2] == (0.0 if j[1] == 0 else 0.7) for j in jobs))


class StatsTests(unittest.TestCase):
    def test_mcnemar(self):
        self.assertEqual(mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(mcnemar_exact(10, 0), 2 / 2 ** 10)

    def test_holm(self):
        self.assertEqual(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    def test_auc(self):
        self.assertEqual(auc([3, 4], [1, 2]), 1.0); self.assertEqual(auc([1], [1]), 0.5)


if __name__ == "__main__":
    unittest.main()
