# Tanya — Business and Technical Trade-off Analysis

PE6201 End-of-Course Project · Individual · TGMOK Holdings cross-division assistant

This analysis covers three trade-offs actually measured while building Tanya, each with a
concrete before/after and a reason for the choice made — not a list of theoretical options.
Full derivations and every number here are logged with dates in `docs/ALIGNMENT.md`.

## 1. Citation grounding: a real bug, and a behaviour that looked like one but wasn't

Screen-recorded testing surfaced Tanya replying "The documents do not say" while still citing
a source — sometimes a fake id (`Cited: <1, 2>`, a leftover bracket number) or the prompt's
own unfilled placeholder text. Root cause: the grounding prompt told the model to cite "the
id" without disambiguating it from the bracket position number shown next to each note, and
one code path (a fresh document upload) had no real id to offer the model in the first place.

Fixed by making the id explicit ("never the bracket number") with a worked example, and by
generating a real id for uploaded content before the model ever sees it. Verified live,
before/after: 0/3 test cases passing before the fix, 3/3 after, with zero malformed citations
across a full 23-question run afterward.

The trade-off worth naming: not every abstention is a bug. An honest "the documents do not
say" with no citation, or with a real (if insufficient) citation, is a defensible "not sure" —
treating it as equivalent to a fabricated citation would have meant chasing a problem that
didn't exist. The evaluation criteria were rewritten to score only the fabrication, which is
the failure mode that actually damages trust.

## 2. Retrieval chunk size: recall against token cost, and why a fix needs re-validating

A reviewer flagged the initial 25-word chunking as too small to hold a full SOP step. Swept
25 through 300 words against the fixed 20-question set (free, code-only — no model calls):
cross-division recall rose from 82% (60 words, the prior default) to 91% at 200 words, and
plateaued through 300. The cost: average words sent per query nearly triples, 286 → 821.
Adopted 200 words as the best recall-per-token point on that curve.

Title-prefixed embedding (prepending each chunk's document title before computing similarity,
at no extra generation cost) was tested alongside this and initially looked free: it lifted
division recall to 100% in aggregate. But re-checked against the single hardest case in the
set (a cross-division question needing a specific CNC tooling spec), title-prefixing actually
ranked the correct document *worse* than plain embedding once chunk size changed — the exact
opposite of what the same knob measured at the old chunk size. The lesson kept in the
notebook rather than smoothed over: a fix's benefit on one case, or even in aggregate under
one config, does not automatically transfer when another parameter changes. Every adopted
change was re-measured against the full set, not just the case that motivated it.

## 3. Reducing over-abstention traded into confident hallucination — and what it costs

Fixing citation format (above) and adopting 200-word/titled retrieval together fixed two
questions that previously abstained when they had enough evidence to answer. But the same
change increased false confidence on questions retrieval still fails: two cases where the
needed document was missing (0/2 documents retrieved for one, 1/2 for the other), the system
answered anyway — one fabricated a specific claim, the other invented a component that
belongs to an unrelated document. Faithfulness (an independent LLM-judge check on whether
every claim is grounded) fell from 100% to 85%, the exact target this project set for itself.

Checked whether a quick fix existed before applying one: sorting all 20 questions by their
top retrieval score, the lowest-scoring question in the entire set answers correctly, while
one of the two now-unfaithful ones scores higher than most correct answers. Retrieval
confidence and answer correctness are only weakly related here — no score threshold separates
the bad answers from the good ones without also blocking several currently-correct ones. The
existing citation-content check (verifying cited figures/dates actually appear in the cited
document) also would not have caught either case, since neither hallucination invents a
number — one invents a fact, the other invents an entire component name. No fix was applied;
the residual risk is named below instead, since guessing at a prompt or threshold change here,
without a way to validate it against the full set first, had already produced one aggregate
regression this project (the title-prefixing reversal above).

**Why this is a business question, not just a technical one.** Modelled against
`eval/cost_model.py`'s own framework (variable model cost, plus a fixed cost for a human
reviewer to redo a wrong or unclear answer — 15 minutes at an analyst's rate, a placeholder
figure): the raw model cost is negligible either way, about $0.0002 per query. But at 85%
faithfulness, the *cost per successful answer* rises to roughly $1.50, almost entirely the
cost of catching and redoing the 15% that are wrong — versus about $0.0002 at 100%. At 200
queries a month that is the difference between $0.03 and $300; at 2,000 queries, $0.31 versus
$3,000. The token bill is not what makes reliability expensive here; the human-review cost of
being wrong is, by roughly three orders of magnitude. Both figures remain far below the
modelled manual (no-Tanya) baseline of ~$5,540/month, so the tool is worth deploying either
way — but the faithfulness gap is the number that should be watched in production, not the
API bill.

## Why no agentic component

Tanya is a single retrieve-then-generate call, not a multi-step agent, by choice: every
question this project needed to answer is a lookup-and-synthesize task over a fixed or
recently-updated document set, not a task requiring tool use, planning, or multi-turn
delegation. Adding agentic orchestration would add cost and failure surface (more model calls,
more places for a plan to go wrong) without addressing any of the three trade-offs above,
which are all about retrieval and grounding quality, not task decomposition.

## What's still open

The confident-hallucination risk in Section 3 is not fixed, and is the most important thing
to monitor if this were deployed: watch faithfulness on live traffic, not just the fixed
evaluation set. A promising but unbuilt mitigation is a named-entity check — verifying that
specific components, ids, or claims in an answer appear somewhere near the cited document, the
same principle as the existing figure-check but for concepts instead of numbers. It was not
built here because it has not been validated against the full evaluation set, and this
project's own experience (Sections 2 and 3) is that an unvalidated fix is as likely to move a
problem sideways as to remove it.
