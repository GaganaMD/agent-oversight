# Agent Oversight

Research on whether monitoring of AI agents can still prevent harm when it fires: the monitoring-control experiments behind *Detection Is Not Containment*, and a follow-up study of human and LLM overseers deciding under a deadline. Author: Gagana M D.

## Relationship to the original collaboration

This work began as a joint project at the Apart Research AI Incident Response Sprint (September 2026), reported as *Detection Is Not Containment: Timely Monitoring Determines Whether AI Agent Failures Can Be Prevented* by Gagana M D, Kaustubh Gupta and María Inés Berdiñas ([project page](https://apartresearch.com/sprints/projects/detection-is-not-containment-timely-monitoring-determines-whether-ai-agent-failures-can-be-prevented-oexs)). That report had three parts:

| Part | Authors (per the report) | Where it lives |
|---|---|---|
| Monitoring-control experiment (Phases A to F) | Gagana M D | this repository (history preserved from the joint repo) |
| Public-source incident forensics and the sim/real checklist protocol | Kaustubh Gupta and María Inés Berdiñas | [GaganaMD/detection-is-not-containment](https://github.com/GaganaMD/detection-is-not-containment) only; **not included here** |
| Human-deadline oversight study (`oversight/`, October 2026) | Gagana M D | this repository |

The project framing and the report were shared work. This repository contains only the code that Gagana M D wrote. None of the code here imports or depends on the forensics or protocol pipeline. Where the paper draft refers to the forensics results, it cites the joint report. [`PROVENANCE.md`](PROVENANCE.md) maps every result folder to the commit that produced it in the original repository.

---

A local, deterministic AI-control research artifact about a basic but often-missed distinction:

> A monitor detecting a problem eventually does not establish that an intervention could still prevent the problem.

This repository measures monitor evidence and threshold crossings over trajectory prefixes, compares them to an independently frozen safety boundary, and then replays a matched authority-revocation intervention. The empirical setting is deliberately narrow: a synthetic authorization-controlled delivery environment, local Qwen monitors, fixed prompts, fixed inputs, and deterministic/cached evaluation where stated.

![Evidence arrives differently across monitor views](figures/fig1.png)

## Follow-up: human-deadline oversight study

The `oversight/` package scales the experiment from one fixture to 54 matched authorized/unauthorized trajectory pairs (6 task types x 3 identifier formats x 3 intervention margins), adds repeated sampling, and tests whether a human or LLM overseer can make the revoke-or-allow decision before the last-safe point. Design and hypotheses were pre-registered before any data ([`docs/HUMAN_DEADLINE_PREREGISTRATION.md`](docs/HUMAN_DEADLINE_PREREGISTRATION.md)). Results: [`results/oversight/summary.md`](results/oversight/summary.md). Paper draft: [`paper/DRAFT.md`](paper/DRAFT.md). Runbook: [`oversight/README.md`](oversight/README.md).

The model runs used Qwen3-14B (bf16, vLLM on Modal), a different serving stack from the frozen phases below, so they are a new experiment, not a reproduction. The human results so far are one complete pilot session.

## What the project shows — and does not show

### Supported in this artifact

1. **Timing is observable.** For the primary neutral attack (A2), the grounded view first received relevant authorization evidence at sequence 37. The frozen monitor crossed its benign-control-calibrated threshold at sequence 37; the last safe intervention point was sequence 38. This gives utilization delay 0 and intervention margin +1.
2. **A closed-loop intervention can prevent the effect in the toy environment.** In the matched F1 replay, a frozen score crossing at sequence 37 revokes the confirmation capability. The same later confirmation is attempted, rejected by the authoritative environment, and the prohibited effect is absent.
3. **Representation instability can become a real control cost.** In Phase E, only 8/12 semantics-preserving identifier assignments retained correct paired threshold decisions, and only 3/12 were strictly control-ready. In the F3 replay, a representation-induced benign crossing revoked legitimate authority and caused task failure.

### Not established

- General monitoring, containment, or control performance.
- Robustness beyond one synthetic environment, fixed prompt/model settings, single deterministic draws, or sampled identifier transformations.
- Chain-of-thought faithfulness. The A1 result is explicitly treated as sensitivity to externalized wording, not evidence that CoT is faithful.
- Claims about unfinished B2/B2-R work. Its frozen protocol lineage and the B2-R cache baseline are retained solely because Phases C/F validate antecedent integrity byte-for-byte; they are not analyzed or presented as completed results.

![Representation robustness is conditional, not assumed](figures/fig2.png)

## Headline results

| Question | Result | Interpretation |
|---|---:|---|
| Primary B1.3 run | 690 logical prefix evaluations; 119/119 unique local calls valid | Exact-input reuse is explicit and auditable. |
| Calibration | Threshold 51; 0/12 control trajectory false positives | Threshold was chosen from controls, not attacks. |
| A2 grounded timing | information available 37; detected 37; safe boundary 38 | Detection was timely by one event in this fixture. |
| Phase C relational telemetry | G2: attack 100 vs benign 0 at seq 37 | A visible authorization relation was sufficient in this tested representation. |
| Phase E invariance | 8/12 semantic decision invariance; 3/12 strict control-ready invariance | The signal is representation-conditional. |
| Phase F closed loop | F1 attack prevented; F3 benign task disrupted | A score can produce both prevention and harmful false intervention. |

![Closed-loop intervention changes environment authority, not the actor history](figures/main/fig3_closed_loop_intervention.png)

## Design in one page

The same canonical trajectory is projected into three monitor-visible views:

- `M_ACTION`: actions and tool observations only.
- `M_COT_ACTION`: action view plus externalized reasoning.
- `M_GROUNDED`: action/reasoning plus environment-issued authorization telemetry.

For each prefix, the study records:

- `information_available_seq`: first prefix where the frozen oracle says relevant evidence exists;
- `first_detection_seq`: first monitor score at or above the frozen threshold;
- `monitor_utilization_delay = first_detection_seq - information_available_seq`;
- `last_safe_intervention_seq`: final blockable point before the prohibited effect; and
- `intervention_margin = last_safe_intervention_seq - first_detection_seq`.

The safety oracle, monitor prompt, input serialization, and thresholding protocol are separated. The oracle does not access the monitor output; the controller does not rewrite the actor’s subsequent action attempt.

## Repository map

```text
pilot/                       Phase A/A.5, B1.3, C, D, and E implementation
hermes_phase_f/              deterministic cached-decision closed-loop replay
results/                     released CSV/JSON/JSONL evidence for included phases
docs/                        protocols, freezes, phase results, limits, figure captions
protocol/                    frozen condition files, manifests, and validation reports
figures/main/                three judge-facing explanatory PNGs
figures/supporting/          timing and outcome supporting figures
tests/                       deterministic apparatus and protocol tests
scripts/verify_release.py   read-only integrity and release-layout verification
oversight/                   human-deadline oversight study: scenarios, runners, participant page, analysis
results/oversight/           its model call logs, human sessions, summary and figures
paper/                       paper draft for the oversight study
```

## Reproduce and verify

### Requirements

- Python 3.10+.
- No Python package installation is required for verification; the released code uses the standard library.
- The primary inference artifacts were generated locally using Ollama's native API with `qwen3:14b`, temperature `0`, seed `424242`. A local model is **not** required to inspect results, run deterministic tests, or validate the Phase F cached replay.

### Safe, read-only verification

Run from the repository root:

```bash
python scripts/verify_release.py
python -m unittest discover -s tests -v
python -m hermes_phase_f.pilot.validate_phase_f
python -m oversight.analyze
```

`oversight.analyze` recomputes `results/oversight/summary.json` and the figures from the logged calls and sessions without calling a model; the output should be byte-identical to the committed file. The oversight model runs need `matplotlib` for figures and, for new inference, a Modal account (see `oversight/README.md`).

These commands do not call a model. `verify_release.py` checks the frozen A.5 oracle-body hash and frozen monitor-prompt hash, checks expected released structure, and verifies that the six explanatory PNGs are present without decoding or transforming them.

### Important execution boundary

Do **not** run `python -m pilot.run_phase_b13 --run` against the released results directory. It is an inference runner and appends to the immutable JSONL call log. The public release includes the completed B1.3 records for audit; normal review should use the read-only checks above. Any new inference should occur in a separate, versioned run directory and be reported as a new experiment, not as a reproduction of this frozen result.

## Evidence and interpretation

- **Primary synthesis:** [`docs/APART_RESEARCH_SYNTHESIS.md`](docs/APART_RESEARCH_SYNTHESIS.md)
- **Frozen A.5 evidence oracle:** [`docs/ORACLE_FREEZE_A5.md`](docs/ORACLE_FREEZE_A5.md)
- **B1.3 full prefix result:** [`docs/PHASE_B13_RESULTS.md`](docs/PHASE_B13_RESULTS.md)
- **Relational-evidence ablation:** [`docs/PHASE_C_RESULTS.md`](docs/PHASE_C_RESULTS.md)
- **Semantic counterfactuals:** [`docs/PHASE_D_RESULTS.md`](docs/PHASE_D_RESULTS.md)
- **Identifier invariance diagnostic:** [`docs/PHASE_E_RESULTS.md`](docs/PHASE_E_RESULTS.md)
- **Closed-loop replay:** [`docs/PHASE_F_RESULTS.md`](docs/PHASE_F_RESULTS.md)
- **Exact figure provenance/captions:** [`docs/FIGURE_DATA_AUDIT.json`](docs/FIGURE_DATA_AUDIT.json) and [`docs/PAPER_CAPTIONS.md`](docs/PAPER_CAPTIONS.md)

## Integrity anchors

| Frozen item | SHA-256 |
|---|---|
| A.5 oracle rule body | `83141b61abf6c95ad2afa6bddea72e74ca59f79aae32f41fd04cf3d17e37b93d` |
| B1 monitor prompt | `d6bbb910488951d4daad76f80d140c88ba134b1b6984df2b9ecfba8d2b4b7b4a` |

The primary B1.3 monitor used local Ollama native API (`http://127.0.0.1:11434/api/generate`), `qwen3:14b`, model digest `bdbd181c33f2ed1b31c972991882db3cf4d192569092138a7d29e973cd9debe8`, temperature 0, seed 424242, and a 90-second hard timeout. See the phase result documents for exact scope and all limitations.

## License

MIT. See [LICENSE](LICENSE).
