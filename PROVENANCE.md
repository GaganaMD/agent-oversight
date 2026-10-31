# Provenance

This repository was split out of the joint repository
[GaganaMD/detection-is-not-containment](https://github.com/GaganaMD/detection-is-not-containment)
on 2026-10-31. It keeps only work authored by Gagana M D. The joint repository and all its
branches are unchanged and remain the record of the collaboration.

## How the split was made

1. History up to commit `d15876e` (2026-09-15) was fetched by hash from the joint repository.
   Every commit in that range is by Gagana M D. The forensics and protocol commit `c567d92`
   (Kaustubh Gupta) and the merge `e209137` come after it and are not in this history.
2. The October oversight work was copied file by file from joint-repository commit `ff2f0da`
   (branch `human-deadline-study`) using `git archive`, limited to these paths:
   `oversight/`, `tests/test_oversight.py`, `docs/HUMAN_DEADLINE_PREREGISTRATION.md`, `paper/`,
   `results/oversight/`. It enters this history as one commit.
3. Not copied: `claims/`, `forensics/`, the non-frozen files in `protocol/` (checklist rubric,
   stance sheets, scorers, case sheets), `docs/LITERATURE_REVIEW.md`, `docs/DUAL_USE.md`, and
   the README, `docs/RELEASE_SCOPE.md` and `.gitignore` lines added in `c567d92`. Revisions made
   to the checklist scoring in `287e85a` also stay in the joint repository, because they modify
   co-authored code.
4. Documentation was then edited here: README (relationship section), `paper/DRAFT.md` (the
   forensics section now cites the joint report), `CITATION.cff`, and this file.

## Where each result came from

| Results | Produced by | Joint-repository commit |
|---|---|---|
| `results/phase_*`, `figures/`, `docs/PHASE_*` | Phases A to F, local Ollama `qwen3:14b` (see `README.md`, Integrity anchors) | `c0a2e92`, `9565ea5` (also in this history) |
| `results/oversight/monitor_calls.jsonl`, `overseer_calls.jsonl` | `oversight/run_monitor.py`, `run_overseer.py`; Qwen3-14B bf16 on vLLM 0.9.2 (Modal), 2026-10-29 | code as of `287e85a`; logs committed in `ff2f0da` |
| `results/oversight/human/p1.json` | One participant session from the study page, received through its copy-out box, 2026-10-29 | `ff2f0da` |
| `results/oversight/summary.*`, `fig_*.png` | `oversight/analyze.py` | `ff2f0da` |
| `docs/HUMAN_DEADLINE_PREREGISTRATION.md` | Written before any model call or response | first committed in `287e85a`; deviations added in `ff2f0da` |

The call logs record the Modal endpoint URL that served them. That deployment is stopped, and it
accepted requests only with an API key that is not stored anywhere in this repository.

## Checks run after the split

* All unit tests pass (`python -m unittest discover -s tests`).
* `python scripts/verify_release.py` and `python -m hermes_phase_f.pilot.validate_phase_f` pass.
* `python -m oversight.analyze` regenerates `results/oversight/summary.json` byte-identical to the
  copied file.
* `git cat-file -t c567d92` fails here: the forensics commit is not in this repository.
