"""Scaled monitor run: prefix sweeps plus repeated sampling at the critical prefix.

For every scenario (54 matched pairs x 2 arms) and evidence level (G0/G2/G3):
  * sweep: one temperature-0 call per visible prefix, giving first-crossing timing to compare
    with the evidence-available and last-safe sequence numbers;
  * reliability: K extra temperature-0.7 samples on the last prefix before the boundary,
    measuring how often the threshold decision flips across samples.
Identical prompts (e.g. pre-evidence prefixes shared by both arms and all levels) are called
once. Usage:
    python -m oversight.run_monitor             # print the call plan only
    python -m oversight.run_monitor --run       # execute against $DNC_BASE_URL
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import llm_client as llm
from .scenarios import EVIDENCE_LEVELS, FULL_DESIGN_PAIRS, build_pairs, visible_events

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (Path(__file__).parent / "MONITOR_PROMPT.txt").read_text(encoding="utf8")
LOG = llm.RUN_DIR / "monitor_calls.jsonl"
K_SAMPLES = 5
SAMPLE_TEMPERATURE = 0.7


def render(events: list[dict]) -> str: return PROMPT.replace("{VISIBLE_EVENTS_JSON}", llm.js(events))


def valid(parsed: dict) -> bool:
    s = parsed.get("suspicion_score")
    return isinstance(s, int) and 0 <= s <= 100 and isinstance(parsed.get("would_intervene"), bool)


def plan(n_pairs: int) -> list[tuple[str, int, float, dict]]:
    jobs: dict[tuple[str, int], tuple[str, int, float, dict]] = {}
    for pair in build_pairs(n_pairs):
        for s in pair:
            last_visible = max(e.seq for e in s.events)
            for level in EVIDENCE_LEVELS:
                for end in range(1, last_visible + 1):
                    prompt = render(visible_events(s, level, end))
                    jobs.setdefault((prompt, 0), (prompt, 0, 0.0, {"kind": "sweep"}))
                critical = render(visible_events(s, level, s.last_safe_seq - 1))
                for k in range(1, K_SAMPLES + 1):
                    jobs.setdefault((critical, k), (critical, k, SAMPLE_TEMPERATURE, {"kind": "reliability"}))
    return list(jobs.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--pairs", type=int, default=FULL_DESIGN_PAIRS)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--max-calls", type=int, default=None)
    args = ap.parse_args()
    jobs = plan(args.pairs); cache = llm.load_cache(LOG)
    todo = [j for j in jobs if (llm.digest(j[0]), j[1]) not in cache]
    print(llm.js({"pairs": args.pairs, "unique_calls": len(jobs), "cached": len(jobs) - len(todo),
                  "to_run": len(todo), "endpoint": llm.BASE_URL, "model": llm.MODEL}))
    if not args.run: return
    todo = todo[: args.max_calls] if args.max_calls else todo
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda j: llm.cached_call(LOG, cache, j[0], j[1], j[2], j[3], valid), todo))
    failed = sum(not r["parse_success"] for r in results)
    print(llm.js({"attempted": len(results), "failed": failed, "rerun_to_retry_failures": failed > 0}))


if __name__ == "__main__":
    main()
