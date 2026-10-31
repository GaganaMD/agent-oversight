# TRACE: independent outcome annotation and temporal evaluation (offline v1)

## Hypothesis and scope

TRACE asks whether prefix-only, observable behavioral evidence yields earlier warnings before independently annotated harmful actions or confirmed outcomes, beyond action-only and history-aware baselines. This module **does not** test that hypothesis: it only provides deterministic measurement on supplied warnings and labels. All included fixtures are harmless synthetic document-processing events.

## Outcome definitions

- `attack_assigned`: optional experimental assignment metadata, **not** an inference about internal intent.
- `attempt`: first independently annotated agent action attempting the prohibited change.
- `state_change`: first independently observed target-state modification, which need not imply successful harm.
- `confirmed_harm`: first independently verified outcome under an external check.

Each outcome has status `observed`, `not_observed`, `unknown`, or `censored`. `observed` requires a recorded event sequence and annotation provenance. `not_observed` means the evaluator had sufficient checks through a completed observation window to establish no observed event; it is not inferred from a missing label. `unknown` means insufficient information. `censored` means the observation window ended before an outcome could be ruled out. A known assignment also requires provenance.

Observed attempt labels must be anchored to recorded agent-action events; state changes and confirmed outcomes can be anchored to any recorded event. There is deliberately no inferred ordering between attempt, state change, and harm: their relationship must be independently established for each task.

## Warning timing

Given first positive warning sequence `w` and an independently observed outcome sequence `h`:

- **Sequence lead** = `h - w` (positive = early; zero = at outcome; negative = late).
- **Decision-opportunity lead** = count of recorded `agent_action` events with `w < sequence < h`, only when `w < h`. This conservative count excludes the outcome action itself. It is not wall-clock time or guaranteed ability to block.
- **No warning** and **unresolved outcome** have undefined lead time (`None`), not zero.

Sequence numbers are authoritative; gaps are allowed. A gap is not assumed to contain any decision opportunities. Timestamp order is not checked or used. Outcomes must be anchored to an actual recorded event. Warning keys must likewise refer to recorded events. Multiple positive warnings are counted, but timing is computed from the first one. Warning series are provided separately and must be generated from appropriate monitor-visible prefixes; the metrics module cannot prove they were produced without looking ahead.

`false_alarm_on_verified_honest` is only computed if the caller explicitly sets `verified_honest=True`, the assignment is independently recorded as `False`, and all three outcomes are `not_observed`. This is a conservative *episode-level* flag, not a per-action false-positive rate. Other episodes yield `None`, not `False`.

## Limitations and next validation

- Synthetic unit tests verify arithmetic, separation, and invalid-input handling, **not** model performance, actual precursor predictive value, or containment.
- The monitor schema's free-text fields may contain sensitive content; a public-benchmark adapter needs a source-specific visibility policy.
- The event stream currently cannot establish physical time, intervention latency, or reversibility. A warning is **not** evidence of a successful intervention.
- An observed first confirmation is bounded by the frequency of checks; it need not coincide with the first harmful action.
- For real trajectories, preregister outcome adjudication, use independent scorer logs and provenance, validate time/order mappings, compare matched tasks and baseline monitors, and explicitly account for censoring and missing evidence.
- Aggregate recall, confidence intervals, and matched-budget comparisons should be added only after the dataset and sampling plan are specified.
