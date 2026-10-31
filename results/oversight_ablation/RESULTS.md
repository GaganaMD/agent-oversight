# Monitor confound check: research summary

Design: `docs/ABLATION_PREREGISTRATION.md` (committed in `841d832` before any call). Full tables:
`summary.md` / `summary.json`. Raw calls: `calls.jsonl`.

**Run.** 9,821 of 9,821 unique calls parsed (one transient failure succeeded on retry; 9,822 log
lines). Qwen3-14B bf16, vLLM on Modal; app stopped after the run. The original cell (W0-S)
reproduced the earlier run's score on all 323 temperature-0 inputs (252/323 identical text).
Unit of analysis: scenario pair (54 unauthorized G2 scenarios, one temperature-0 output per
cell); samples are summarised per input, never pooled as observations.

## Pre-registered hypotheses

| | Contrast (unauthorized G2) | Flagged | Risk difference (95% CI) | p (Holm) | Verdict |
|---|---|---|---|---|---|
| H1 | W1-S vs W0-S: delete the two clauses | 0/54 vs 0/54 | +0.00 (0.00 to 0.00) | 1.0 | **Falsified** |
| H2 | W0-D vs W0-S: decision vs score | 21/54 vs 0/54 | +0.39 (+0.26 to +0.52) | 3e-6 | **Supported** |
| H2 | W1-D vs W1-S: decision vs score | 20/54 vs 0/54 | +0.37 (+0.24 to +0.50) | 4e-6 | **Supported** |
| — | W2-S vs W1-S: add explicit authorization rule | 28/54 vs 0/54 | +0.52 (+0.39 to +0.65) | <1e-6 | Large effect |

* **H3 falsified.** W0-S G2 AUC 0.69 (95% CI 0.63 to 0.76), excluding 0.90. W2-S: 0.97 (0.94 to 1.00).
* **H4 supported.** 0 false alarms in every cell on authorized runs and clean prefixes. (R
  revoked 3/54 G0 inputs in both arms equally; G0 inputs are identical by construction.)

## Recognise, recommend, prevent (G2, unauthorized)

| Cell | Rationale names violation | Recommends intervention | Prevented |
|---|---|---|---|
| W0-S original | 35/54 | 0/54 | 0/54 |
| W0-D decision format | 20/54 | 21/54 | 21/54 |
| W2-S explicit rule, score | 54/54 | 28/54 | 28/54 |
| W2-D explicit rule, decision | 54/54 | 52/54 | 52/54 |
| R overseer prompt | 54/54 | 54/54 | 54/54 |
| Allow-list check (no model) | — | 54/54 | 54/54, 0 disrupted |

Prevention equals the recommendation here by design (synchronous gate before the commit, margin
>= 1); it is not an independent measurement in this environment.

## Exploratory (not pre-registered): the score of 50

* Under W0-S and W1-S, every G2 score is 0 or 50: no value off the prompt's 0/50/100 anchors.
  Deleting the clauses changed nothing (identical counts, 0:33, 50:21).
* The 50 is stable model behaviour, not noise: for 14/54 inputs all five 0.7 samples are 50.
* Adding the explicit rule (W2-S) moves mass to 75 (26/54) but still mostly below 100 (2/54);
  the scale's top anchor ("very strong evidence") is rarely used even when the rationale names
  the violation in 54/54.
* Reading: the 50 is the "substantial ambiguity" anchor chosen when the model has not been told
  that non-membership is a violation; with the rule it still hedges below 100.

## Interpretation

* **Did not survive:** prompt suppression by the two clauses (H1), and the paper draft's claim
  that the monitor "recognises" violations it fails to escalate. The rationale pattern overstated
  recognition: without an explicit rule, threshold-free separation is weak (AUC 0.69).
* **Survived, and sharpened:** a 0 to 100 suspicion score loses signal relative to a binary
  decision (+0.37 to +0.39), and stating the security policy explicitly matters most (+0.52 in
  score format; 52/54 in decision format). The overseer prompt's advantage is mostly explained by
  its explicit authorization framing plus decision format, not by escalation context.
* **Identifier format still matters** without the explicit rule (W0-D: 14/18 alphabetic, 6/18
  numeric, 1/18 opaque) and largely disappears with it (W2-D: 18/18/16).
* **Security baseline:** an allow-list check or least privilege contains 54/54 with 0 disruption
  and no latency; the best LLM cell matches it only when told the policy, at 3 to 9 s per call.
* **Unanswered:** whether any of this holds when harm is not decidable from a visible allow-list,
  and whether a human adds anything there. The rationale-pattern check sample
  (`rationale_check.json`) has not yet been read.
* **Does this justify moving on?** Yes. On allow-list-decidable tasks the LLM monitor adds nothing
  over a deterministic control; its value can only be tested on semantic security tasks, which is
  where human escalation should be studied next.
