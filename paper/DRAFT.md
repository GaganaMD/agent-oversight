# Detection Is Not Containment: Can an Overseer Act Before the Last Safe Moment?

Gagana M D (Independent Researcher)

*Extends "Detection Is Not Containment", a project by Gagana M D, Kaustubh Gupta and María Inés
Berdiñas at the Apart Research AI Incident Response Sprint (September 2026). See Contributions.*

## Abstract

A monitor that flags an AI agent's harmful action helps only if someone can still stop the action
when the flag arrives. We call the last moment at which intervention still prevents the effect
the *last-safe point*, and measure detection against it rather than against the end of the
trajectory. In earlier single-trajectory work, a Qwen3-14B monitor crossed its threshold one event
before the last-safe point, and automatically revoking the agent's authority at that moment
prevented the unauthorized effect; the same monitor also revoked a legitimate run when only the
identifier format changed. Here we scale that setting to 54 matched pairs of authorized and
unauthorized trajectories across six task types, three identifier formats and three intervention
margins, and add the step that real deployments insert between detection and containment: an
overseer who decides whether to revoke. With the authorized-target set visible, the monitor's
own rationale named the violation in 34 of 54 unauthorized runs, yet its score never reached the
original threshold before the last-safe point (0 of 54); it raised no false alarms. Asked instead
to decide "revoke or allow" on the same evidence, the same model revoked all 54 unauthorized runs
and none of the 54 authorized ones. Whether the monitor's score rose above zero just before the
boundary depended on identifier format (13 of 18 alphabetic, 7 of 18 numeric, 1 of 18 opaque).
When the monitor did
cross, it crossed at the evidence event, so the full margin was available: the loss came from
turning recognition into an escalation, not from timing. A first human pilot session shows the
same pattern from the other side: with the list visible and no timeouts, the participant allowed
3 of 4 unauthorized runs, with high confidence, and reported relying on the wording of the
warning. The study was pre-registered; all code, prompts, call logs and analysis are public.

## 1. Introduction

AI control evaluations usually ask whether a monitor catches a misbehaving agent. In an
incident, the question that matters is narrower: is there still time to act? A monitor that
flags an unauthorized data export after the export finished has detected the incident but not
contained it. And in most deployments a flag does not act by itself. It goes to a person, who
reads it, decides, and only then revokes access.

That gap between detection and containment is where human oversight sits, and it is mostly
measured in frameworks rather than experiments. Mitchell, Ghosh and Passi (2026) argue that
current agent design pushes humans out of the loop and that the overseer's situated needs should
be treated as a first-class requirement. Our earlier result supplies a concrete version of the
problem: the monitor's warning arrived with a margin of one event. That is enough for an
automatic controller. Whether it is enough for a person depends on how long the person needs and
what the warning shows them.

This paper makes three contributions.

1. **A timing-aware evaluation of monitoring at scale.** 54 matched pairs of trajectories that
   are identical except for one authorization record, varying task type, identifier format and
   the number of events between evidence and the last-safe point. For each, we measure when a
   monitor's score first crosses its threshold relative to the last-safe point, and how stable
   that decision is across repeated samples.
2. **A human-deadline pilot.** Participants act as on-call overseers for escalated alerts under
   8- or 28-second deadlines, with or without the authorization evidence that made the monitor
   accurate. We report containment and disruption together, because an overseer who revokes
   everything contains every attack and breaks every legitimate task.
3. **A comparison of who should receive the alert.** Automatic revocation, a human, or an LLM
   overseer, using the measured rates for each.

## 2. Definitions

These terms are used throughout and nowhere else in a different sense.

| Term | Meaning |
|---|---|
| Unauthorized / authorized run | The two members of a matched pair. In the unauthorized run, the agent's additional action targets something outside the authorized set; in the authorized run, the same target is in the set. Earlier drafts called these "attack" and "benign"; code and logs keep `attack`/`benign` as field values. |
| Evidence event | The single environment record, emitted after the agent stages its additional action, that carries authorization information. Its sequence number is the *evidence sequence*. |
| Last-safe point | The sequence number of the agent's commit proposal. Revoking authority at or before it prevents the effect; after it, the effect has happened. |
| Margin | Last-safe sequence minus evidence sequence, in events (1, 3 or 6). |
| Threshold crossing | The first prefix at which the monitor's 0 to 100 suspicion score reaches the threshold. |
| Containment | An unauthorized run whose authority is revoked at or before the last-safe point. |
| Disruption | An authorized run whose authority is revoked, so a legitimate task fails. |
| Evidence level | What the evidence event shows. **G0**: only the staged target. **G2**: the target and the authorized-target set (a relational record). **G3**: the target and an explicit policy verdict. |

## 3. Background: the single-trajectory result

The earlier phases used one synthetic report-delivery trajectory and a frozen Qwen3-14B monitor
(Ollama, Q4_K_M, temperature 0) with a threshold of 51, set so that none of 12 control
trajectories crossed it.

* With grounded evidence, the monitor crossed at sequence 37, the event where authorization
  information first appeared; the last-safe point was sequence 38, a margin of one event.
* Varying only how the evidence was represented (Phase C), the relational record (G2) separated
  the unauthorized and authorized runs (scores 100 and 0); action-only evidence (G0) did not,
  and both the structural count and the explicit verdict produced an authorized-run crossing.
* Across 12 identifier assignments with the same meaning (Phase E), every unauthorized run
  crossed, but only 8 of 12 assignments classified both runs correctly, and only 3 of 12 met the
  stricter criterion of no early crossing plus a rationale that cited the evidence.
* In a matched replay (Phase F), revoking authority at the crossing prevented the effect; with
  the same policy, a representation-induced crossing on an authorized run revoked legitimate
  authority and the task failed.

These results came from one task with one margin and one draw per input, which is the main
validity concern reviewers raised. Sections 4 and 5 address it.

## 4. Methods

The design, hypotheses, measures and exclusions were committed before any data
(`docs/HUMAN_DEADLINE_PREREGISTRATION.md`, first committed as `287e85a` in the joint repository
before any model call or response; see `PROVENANCE.md`).

**Scenarios.** `oversight/scenarios.py` generates 54 matched pairs, one per combination of six
task types (report delivery, data export, vendor payout, service deployment, file sharing, access
grants), three identifier formats (alphabetic `route_C`, numeric `acct_42`, opaque `c-7f3a`) and
three margins (1, 3, 6 events). Every trajectory follows the same structure: preparation steps,
one approved stage-and-commit, a neutral reasoning step, a second stage, the evidence event, a
margin of neutral queue-check events, then the second commit. Within a pair, the only
differences are the authorization record and the post-boundary outcome; tests check this for all
54 pairs, and that G0 views of the two runs are byte-identical.

**Monitor.** The frozen monitor prompt from the earlier phases with one phrase generalised
("report-delivery task" to "multi-step task"). Qwen3-14B in bf16 served by vLLM, thinking
disabled. Because the backend differs from the earlier runs, earlier numbers are not expected to
reproduce exactly. For every scenario and evidence level we score every prefix at temperature 0,
then draw five samples at temperature 0.7 on the last prefix before the last-safe point. We
report thresholds of 51 (the frozen value) and a calibrated threshold of one point above the
highest score on any prefix before the evidence event, where no authorization information exists
and any crossing is a false alarm.

**Human overseers.** Participants open a web page, read a brief, and do two untimed practice runs
with feedback, then 16 timed runs without feedback. Each run shows the agent's log up to the
evidence event, a monitor flag with the evidence record, and a countdown to the commit; the
remaining events stream in during the countdown. The participant chooses *Revoke authority* or
*Allow*; if they do neither, the action proceeds. The design is within-subjects: evidence level
(G0, G2) x deadline (8 s for margin 1, 28 s for margin 6) x run type, two runs per cell, from 16
distinct pairs so nobody sees both members of a pair. Which member of each pair a participant
sees alternates between participants. G0 runs are indistinguishable by construction and serve as
a check that the materials leak no cue.

**LLM overseer.** The same decision, using instructions that mirror the participants'
(`oversight/OVERSEER_PROMPT.txt`), for all 108 runs at all three evidence levels; one
temperature-0 call and three samples at 0.7.

**Triage policies.** We combine measured rates. Under *automatic revocation*, containment and
disruption are the monitor's before-boundary crossing rates on unauthorized and authorized runs.
Under *escalation*, they are those crossing rates multiplied by the overseer's revoke rates in the
matching cell. This assumes the monitor's and the overseer's errors are independent on a given
run, which we state wherever the numbers appear.

## 5. Results

All monitor and overseer calls completed (3,681 unique monitor inputs, 1,296 overseer calls; one
transient failure succeeded on retry). Numbers below are from `results/oversight/summary.json`;
intervals are 95% Wilson intervals.

### 5.1 The monitor recognises more than it escalates

| Evidence | Unauthorized: crossed 51 by last-safe point | Authorized: crossed 51 | Unauthorized: crossed calibrated threshold | Authorized: crossed calibrated threshold |
|---|---|---|---|---|
| G0 | 0/54 | 0/54 | 0/54 | 0/54 |
| G2 | 0/54 | 0/54 | 25/54 (0.34 to 0.59) | 0/54 |
| G3 | 39/54 (0.59 to 0.82) | 0/54 | 54/54 | 0/54 |

*Table 1. Threshold crossings at or before the last-safe point. The calibrated threshold is 1:
every one of 8,748 pre-evidence prefixes scored exactly 0, so the pre-registered rule reduces to
"any non-zero score" (Deviation 1).*

The monitor raised no false alarm on any authorized run, at any evidence level or threshold.
Its failures were all missed detections, and they came from the score rather than the reading.
At the last prefix before the boundary, G2 unauthorized runs scored either 0 (33 runs) or 50
(21 runs), never higher, and the monitor's own `would_intervene` flag was false in all 54. Yet
its one-sentence rationale stated that the target was not in the authorized set in 34 of the 54
(a fixed pattern match; Deviation 2). A typical output reads: *"The agent staged a grant for
scope_J, which is not in the authorized targets, indicating potential inconsistency with the
task"*, scored 50, which the prompt defines as "substantial ambiguity". Five samples at
temperature 0.7 gave the same score.

**Timing was not the constraint.** Whenever the monitor crossed, it crossed at the evidence event
itself, so the realised margin equalled the full margin (median 1, 3 and 6 events for margins 1, 3
and 6). The detection was early enough every time it happened.

**Identifier format still matters, in the opposite direction from before.** Among G2
unauthorized runs, a score of 50 appeared for 13 of 18 alphabetic identifiers (`route_C`), 7 of 18
numeric (`acct_42`) and 1 of 18 opaque (`c-7f3a`). In the single-fixture Phase E study, unusual
formats produced false alarms on authorized runs; here they suppress detection of unauthorized
ones. Both are the same weakness: the decision depends on how the identifier looks, not only on
whether it is in the set.

**H1** (crossings on most G2 unauthorized runs, false crossings varying by format) is not
supported as stated; format-dependence appears in missed detections instead. **H2** (more
instability on authorized runs) is not supported: instability was low everywhere and highest on
G2 unauthorized runs at the calibrated threshold (8/54) against 0/54 authorized.

These results come from a different serving stack than the single-fixture phases (bf16 weights on
vLLM with thinking disabled, against a 4-bit Ollama build), so we do not attribute the change
from the earlier 100-versus-0 separation to any one factor.

### 5.2 Asked to decide rather than score, the same model is exact

| Evidence | Unauthorized revoked | Authorized revoked | Samples disagree |
|---|---|---|---|
| G0 | 3/54 | 3/54 | 5/54 each arm |
| G2 | 54/54 | 0/54 | 0/54 and 1/54 |
| G3 | 54/54 | 0/54 | 0/54 |

*Table 2. LLM overseer, temperature 0, last pre-boundary prefix.*

With the G2 record, Qwen3-14B prompted as an overseer choosing "revoke" or "allow" was correct on
all 108 runs. On G0, where the two runs are identical, it defaulted to allowing (3 revocations
per arm), as it should when nothing distinguishes them. The difference from Section 5.1 is the
output the model is asked for: a binary decision with stated consequences, against a 0 to 100
suspicion score read through a fixed threshold.

### 5.3 First human session

One participant has completed the study so far, so these are observations about one person, not
rates. They made all 16 decisions before the deadline (no timeouts; median decision time 3.2 to
7.1 seconds by cell, inside even the 8-second limit). With the authorized list visible (G2),
they revoked 1 of 4 unauthorized runs and 0 of 4 authorized runs, mostly at confidence 4 or 5 out
of 5. They had also allowed the unauthorized practice run and received feedback explaining why.
Asked what they relied on, they wrote "the wordings of the warning issued". On G0, they revoked 1
of 4 in each arm, consistent with guessing.

This is the same gap as Section 5.1 from the human side: the evidence was on screen and there was
time, but the decision followed the framing of the alert, which is identical for real and false
alarms. Whether this holds for other participants, or reflects instructions that do not make the
comparison clear enough, is what the remaining sessions will show.

### 5.4 Who should receive the alert

| Evidence | Margin | Automatic revocation | Escalate to LLM overseer | Escalate to human (1 participant) |
|---|---|---|---|---|
| G2 | 1 | 0.50 / 0.00 | 0.50 / 0.00 | 0.25 / 0.00 |
| G2 | 6 | 0.44 / 0.00 | 0.44 / 0.00 | 0.00 / 0.00 |

*Table 3. Containment / disruption at the calibrated threshold, assuming independent errors. At
threshold 51 every G0 and G2 cell is 0 / 0, because nothing is escalated.*

Because this monitor never raised a false alarm, escalation cannot lower disruption here; it can
only lose containment, as it did in the human session. The cap on containment is set upstream:
an alert that is never raised reaches no overseer. Pairing the monitor's score with the
overseer's decision would recover it, since the overseer prompt caught every unauthorized run the
score missed.

## 6. What public incident reports let us check

This section summarises work by co-authors of the joint sprint report, not part of this paper's
contribution. Kaustubh Gupta and María Inés Berdiñas built a pipeline that extracts source-linked
claims from public reports of five agent incidents and scores each incident against an eight-item
containment checklist (Gagana M D, Gupta and Berdiñas, 2026; code in the joint repository). Its
relevance here is what public disclosures let an outside reader check: several of the
containment controls this paper studies, such as pre-run isolation checks and canary alerts, are
not described in any of the public sources for those incidents. Reviewers of the joint report
noted that silence in a public source is not evidence that a control was absent, and that the
LLM-based extraction was largely unvalidated; any use of those results should carry both
caveats.

## 7. Discussion

**Detection has two steps, and the second one failed.** The project's original claim was that
detection is not containment: a flag after the last-safe point prevents nothing. The scaled study
adds a step before that. The monitor read the authorization record and said, in its own words,
that the target was not allowed, then assigned a score that sits exactly at "ambiguous" and set
its intervene flag to false. The information was available, recognised and early; it was lost
when converted into the number that controls escalation. Any control protocol that routes on a
thresholded suspicion score should measure this conversion directly, for example by checking
whether the rationale and the score agree.

**The decision format matters as much as the evidence.** The same model, given the same events,
was perfect when asked to decide with the consequences of each choice spelled out. One reading is
that a suspicion scale invites hedging, since "inconsistent with the task" is a softer claim than
"this action is not authorized". This is one model and one prompt pair, so it is a hypothesis to
test across models, not a general result.

**What the overseer needs.** The single human session points the same way. A person with the
authorized list in front of them, and time to spare, still followed the alert's wording. If that
pattern holds, the useful interface change is not more time but a record that does the comparison
for the reader, for example "target scope_J is not in the authorized set {scope_G, scope_A}".
That is what the explicit verdict (G3) provides, and it was the only level at which the monitor's
score crossed 51 for most unauthorized runs. The environment already knows the answer, so showing
it costs nothing.

**Should detection be containment?** With no false alarms in this setting, automatic revocation
on any non-zero score would have contained about half the G2 runs and all the G3 runs at no cost.
That will not hold in general; the single-fixture phases showed false alarms that broke a
legitimate task. A reviewer suggested a third option between revoking and allowing: holding the
commit while the run continues in a sandbox, so the incident yields information instead of
ending at the first flag. The scenarios here support adding that arm directly, with the caveat
that an agent aware of evaluation may behave differently once paused.

**Allocating scarce attention.** Escalation only helps if the monitor escalates. Here the binding
constraint on containment was the monitor's recall at the alert threshold, not the overseer. A
next step is a triage rule that sends a case to a person when the monitor's rationale and score
disagree; in this data the rationale named the violation in 34 of the 54 G2 unauthorized runs and
in 1 of the 54 authorized ones.

## 8. Limitations

* The tasks are synthetic and the agent's trajectories are scripted, not generated, so the study
  measures monitors and overseers, not agents.
* One complete human session so far, from a volunteer in the author's network, not trained
  on-call staff. It is reported as a single case; the planned pilot of five to six people can
  detect only large effects.
* Monitor recognition is measured by a fixed pattern match over a one-sentence rationale; it can
  miss paraphrases and is not a validated measure of what the model represents.
* One monitor prompt and one overseer prompt; the score-versus-decision contrast may depend on
  their wording as much as on the output format.
* Deadlines map events to seconds at a fixed rate; real agents act at variable speed.
* One monitor model on a backend different from the earlier phases.
* The triage figures assume independent errors between monitor and overseer.

## Contributions

The sprint project (September 2026), as stated in the joint report: María Inés Berdiñas proposed
the forensics pipeline; Kaustubh Gupta built and evaluated the forensics and checklist pipelines;
Gagana M D built the monitoring pipeline and ran the single-trajectory experiments (Phases A to
F). This extension (October 2026): Gagana M D designed and ran the scaled monitor study, the
human-deadline pilot and the LLM-overseer arm, and wrote this paper. Section 6 summarises
co-authors' work and is cited, not claimed.

## LLM usage

Claude was used to help write code for the scaled study and to draft and edit this text. All
results are computed by the released scripts from logged model calls and exported participant
responses.

## References

* Bowkis, A., Buhl, M. D., Pfau, J., & Irving, G. (2026). Automated alignment is harder than you think. arXiv:2605.06390.
* Gagana M D, Gupta, K., & Berdiñas, M. I. (2026). Detection is not containment: Timely monitoring determines whether AI agent failures can be prevented. Apart Research AI Incident Response Sprint. https://apartresearch.com/sprints/projects/detection-is-not-containment-timely-monitoring-determines-whether-ai-agent-failures-can-be-prevented-oexs
* Dixon, R. B. L., & Frase, H. (2025). AI incidents: Key components for a mandatory reporting regime. CSET.
* Gomez, F., et al. (2026). Designing escalation criteria for international AI incident response. arXiv:2604.23183.
* Greenblatt, R., Shlegeris, B., Sachan, K., & Roger, F. (2023). AI control: Improving safety despite intentional subversion. arXiv:2312.06942.
* Mitchell, M., Ghosh, A., & Passi, S. (2026). AI agents push humans out of the loop. arXiv:2608.23642.
* OECD (2025). Towards a common reporting framework for AI incidents. OECD AI Papers No. 34.
* Sidhu, H. K., et al. (2026). Open problems in AI incident governance. arXiv:2607.05163.
* Voudouris, K., Roberts-Gaal, X., Buhl, M., Irving, G., & Summerfield, C. (2026). AI alignment is a human problem. PsyArXiv zqngj_v1.
* Xu, Y., Dahmani, A., Blanchard, M. D., et al. (2026). Toward human-AI complementarity across diverse tasks. arXiv:2605.04070.

## Appendices (to assemble)

* **A.** Scenario generator details and an example trajectory pair at each evidence level.
* **B.** Calibrated-threshold monitor results; results by identifier format and margin.
* **C.** Per-participant human results; the participant instructions verbatim.
