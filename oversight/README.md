# Human-deadline oversight study

Extends the monitoring experiment from one fixture to 54 matched attack/benign pairs, and asks
whether an overseer (a person, or an LLM) can make the revoke-or-allow call before the last-safe
point. Design, hypotheses and analysis plan: [`docs/HUMAN_DEADLINE_PREREGISTRATION.md`](../docs/HUMAN_DEADLINE_PREREGISTRATION.md).

| File | Role |
|---|---|
| `scenarios.py` | Deterministic matched trajectories: 6 task skins x 3 identifier morphologies x 3 margins |
| `MONITOR_PROMPT.txt`, `run_monitor.py` | Prefix sweep (temperature 0) + 5 samples at the critical prefix |
| `OVERSEER_PROMPT.txt`, `run_overseer.py` | LLM overseer on the same escalated alerts humans see |
| `study_design.py`, `build_study.py`, `study/` | Human trial lists and the participant page |
| `analyze.py` | Every reported number and figure, from logged calls and exported responses |
| `modal_vllm.py`, `llm_client.py` | Qwen3-14B on Modal (OpenAI-compatible), cached append-only call log |
| `mock_endpoint.py` | Rule-based stand-in for pipeline tests only. Never a result |

## Runbook

**1. Model runs (about 5,000 calls; expect $2 to $5 of Modal time).**

```bash
pip install modal
```
```bash
modal setup
```
```bash
modal secret create dnc-vllm-key DNC_API_KEY=<long random string>
```
```bash
modal deploy oversight/modal_vllm.py
```

Set `DNC_BASE_URL` to the printed URL plus `/v1`, and `DNC_API_KEY` to the same string. The first
request waits a few minutes while the weights load. Then:

```bash
python -m oversight.run_monitor --run --max-calls 20
```
```bash
python -m oversight.run_monitor --run
```
```bash
python -m oversight.run_overseer --run
```
```bash
modal app stop dnc-qwen3-monitor --yes
```

Re-running a command resumes from the log in `results/oversight/` and retries only failed calls.

**2. Human pilot.** Share the study artifact from its Share menu with each participant (they need
access that lets them use the page, not view-only). Give each person a different participant
number (1, 2, 3, ...); numbers decide which arm of each pair they see. Responses save to the
artifact's `responses` collection. If saving fails, the page shows a copy-out box; save what they
send you as `results/oversight/human/p<N>.json`.

To export saved responses, ask Claude to list the artifact's `responses` collection into
`results/oversight/human/`, or copy each document there by hand.

**3. Analyse.**

```bash
python -m oversight.analyze
```

Writes `results/oversight/summary.md`, `summary.json` and figures.

## Testing without a GPU

```bash
python -m oversight.mock_endpoint
```

In a second shell, point `DNC_BASE_URL` at `http://127.0.0.1:8001/v1` and `DNC_RUN_DIR` at a
scratch directory (never `results/oversight`), then run the three commands above.
