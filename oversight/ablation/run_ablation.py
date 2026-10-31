"""Run the monitor confound check (docs/ABLATION_PREREGISTRATION.md).

Seven prompt cells x 324 unique inputs at temperature 0, plus 5 temperature-0.7 samples on the
G2 and G3 last-before-boundary inputs. Calls are cached in an append-only log, so re-running
resumes and retries only failures.
    python -m oversight.ablation.run_ablation                 # call plan only
    python -m oversight.ablation.run_ablation --smoke         # 10 calls per new format
    python -m oversight.ablation.run_ablation --run
"""
from __future__ import annotations
import argparse, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .. import llm_client as llm
from ..scenarios import FULL_DESIGN_PAIRS, build_pairs, visible_events
from ..study_design import task_brief
from .prompts import CELLS, cell_format, cell_template

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("DNC_ABLATION_DIR", ROOT / "results" / "oversight_ablation"))
LOG = OUT_DIR / "calls.jsonl"
K_SAMPLES = 5
SAMPLE_TEMPERATURE = 0.7
SAMPLED_LEVELS = ("G2", "G3")


def render(cell: str, s, level: str, end_seq: int) -> str:
    p = cell_template(cell).replace("{VISIBLE_EVENTS_JSON}", llm.js(visible_events(s, level, end_seq)))
    return p.replace("{TASK_BRIEF}", task_brief(s.skin)) if cell == "R" else p


def inputs(s):
    """(input kind, level, end sequence) for one scenario: the decision point before the
    boundary at each level, and the clean prefix just before the evidence event."""
    out = [(f"boundary_{lv}", lv, s.last_safe_seq - 1) for lv in ("G0", "G2", "G3")]
    out.append(("clean", "G0", s.evidence_seq - 1))
    return out


def valid_for(cell: str):
    if cell_format(cell) == "S":
        return lambda p: isinstance(p.get("suspicion_score"), int) and 0 <= p["suspicion_score"] <= 100 \
            and isinstance(p.get("would_intervene"), bool)
    return lambda p: p.get("decision") in ("revoke", "allow") and isinstance(p.get("confidence"), int) \
        and 1 <= p["confidence"] <= 5


def plan(n_pairs: int = FULL_DESIGN_PAIRS) -> list[tuple[str, int, float, dict]]:
    jobs: dict[tuple[str, int], tuple[str, int, float, dict]] = {}
    for pair in build_pairs(n_pairs):
        for s in pair:
            for cell in CELLS:
                for kind, level, end in inputs(s):
                    prompt = render(cell, s, level, end)
                    meta = {"cell": cell, "input_kind": kind}
                    jobs.setdefault((prompt, 0), (prompt, 0, 0.0, meta))
                    if kind.startswith("boundary_") and level in SAMPLED_LEVELS:
                        for k in range(1, K_SAMPLES + 1):
                            jobs.setdefault((prompt, k), (prompt, k, SAMPLE_TEMPERATURE, meta))
    return list(jobs.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="10 temperature-0 calls for each new decision cell and R")
    ap.add_argument("--workers", type=int, default=48)
    args = ap.parse_args()
    jobs = plan(); cache = llm.load_cache(LOG)
    todo = [j for j in jobs if (llm.digest(j[0]), j[1]) not in cache]
    by_cell = {c: sum(1 for j in jobs if j[3]["cell"] == c) for c in CELLS}
    print(llm.js({"calls": len(jobs), "cached": len(jobs) - len(todo), "to_run": len(todo), "per_cell": by_cell,
                  "endpoint": llm.BASE_URL, "log": str(LOG)}))
    if args.smoke:
        picked = []
        for cell in ("W0-D", "W2-D", "R", "W1-S"):
            picked += [j for j in todo if j[3]["cell"] == cell and j[1] == 0][:10]
        todo = picked
    elif not args.run:
        return
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda j: llm.cached_call(LOG, cache, j[0], j[1], j[2], j[3], valid_for(j[3]["cell"])), todo))
    print(llm.js({"attempted": len(results), "failed": sum(not r["parse_success"] for r in results)}))


if __name__ == "__main__":
    main()
