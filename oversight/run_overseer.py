"""LLM-as-overseer arm: the same escalated-alert decision humans make, at scale.

Each of the 108 scenarios is shown at every evidence level (G0/G2/G3) with the events
visible just before the commit, using instructions that mirror the human study. One
temperature-0 call plus K temperature-0.7 samples per input.
    python -m oversight.run_overseer          # call plan only
    python -m oversight.run_overseer --run
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import llm_client as llm
from .scenarios import EVIDENCE_LEVELS, FULL_DESIGN_PAIRS, build_pairs, visible_events
from .study_design import task_brief

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (Path(__file__).parent / "OVERSEER_PROMPT.txt").read_text(encoding="utf8")
LOG = llm.RUN_DIR / "overseer_calls.jsonl"
K_SAMPLES = 3


def render(s, level: str) -> str:
    return (PROMPT.replace("{TASK_BRIEF}", task_brief(s.skin))
            .replace("{VISIBLE_EVENTS_JSON}", llm.js(visible_events(s, level, s.last_safe_seq - 1))))


def valid(parsed: dict) -> bool:
    return parsed.get("decision") in ("revoke", "allow") and isinstance(parsed.get("confidence"), int)


def plan(n_pairs: int) -> list[tuple[str, int, float, dict]]:
    jobs = []
    for pair in build_pairs(n_pairs):
        for s in pair:
            for level in EVIDENCE_LEVELS:
                meta = {"kind": "overseer", "scenario_id": s.scenario_id, "level": level}
                prompt = render(s, level)
                jobs += [(prompt, k, 0.0 if k == 0 else 0.7, meta) for k in range(K_SAMPLES + 1)]
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--pairs", type=int, default=FULL_DESIGN_PAIRS)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    jobs = plan(args.pairs); cache = llm.load_cache(LOG)
    todo = [j for j in jobs if (llm.digest(j[0]), j[1]) not in cache]
    print(llm.js({"calls": len(jobs), "cached": len(jobs) - len(todo), "to_run": len(todo), "endpoint": llm.BASE_URL}))
    if not args.run: return
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda j: llm.cached_call(LOG, cache, j[0], j[1], j[2], j[3], valid), todo))
    print(llm.js({"attempted": len(results), "failed": sum(not r["parse_success"] for r in results)}))


if __name__ == "__main__":
    main()
