# Tanya — business and technical trade-offs

PE6201 End-of-Course Project · Trixie Grace Mok. Every number comes from a file in `results/`.

## 1. What I built, and how well it works

Leaders at TGMOK Holdings (F&B, CNC and jewellery divisions) need answers that combine three
divisions' private, changing documents, which no model has seen. Tanya is retrieval-augmented
generation (RAG): it retrieves the relevant notes, answers only from them and cites them. It also
briefs leaders on what a newly filed document connects to.

I measured it against a non-AI baseline, keyword (TF-IDF) search over the same chunks, on 20
questions fixed before anything ran (`results/summary.md`, final run):

| measure | Tanya | keyword baseline | target |
|---|---|---|---|
| answer correctness (every key fact present) | 85% | 75% | |
| correctness, cross-division questions | 73% | 55% | |
| faithfulness (every claim supported by the notes) | 84% | 100% | 85% |
| cross-division recall (every needed division retrieved) | 100% | 91% | 80% |

Tanya wins on retrieval and correctness; the baseline is more faithful, and Tanya is one answer
short of the target. In two checks I graded 20 of the judge's
verdicts myself and agreed with all 20 (`results/judge_agreement.md`).

**Why retrieval, not the whole corpus in the prompt?** All 18 documents fit in one prompt at 2.6
times the tokens, but years of documents will not, and retrieval is where access control belongs.

**Why not an agent?** An agent earns its place when the steps vary with the input and objective
feedback corrects each step (Class 4). Every Tanya question takes the same steps. Searching again
after a miss is a fixed rule in code, not the model's judgement, which fails exactly when it answers
without the documents it needed. So Tanya is a workflow, and a person checks
its output.

## 2. Build or rent, and what it costs

| layer | own or rent | why |
|---|---|---|
| interface | rent Streamlit | no front end to maintain |
| orchestration | own | the grounding and hand-off logic is the product |
| retrieval, vector store | own | numpy in memory: 21 chunks need no database |
| embeddings | rent `all-MiniLM-L6-v2`, run locally | no per-call price; documents stay local |
| generation | rent `gpt-4o-mini` via OpenRouter | $0.15/$0.60 per million tokens |
| evaluation, guardrails | own | only I know what a right answer from these documents is |

Of Class 2's five build-or-buy factors, data gravity and control decided it. I skipped no-code RAG
builders: they hide the retrieval step I measure.

**Cost per successful answer** (`results/cost_model.md`). A question is one model call of about
1,900 tokens: $0.0003. People cost the rest (assumed in `config.py`): a 3-minute check of every
answer ($2.00) and a 15-minute redo of each wrong one ($10, the same as answering by hand). By the
course's break-even formula, Tanya beats answering by hand once over 20% of answers are right; at
85% it costs $3.50 per answer against $10. With $181 a month of fixed costs, 200 questions cost
$881 against $2,000. Checking time, not token price, moves the break-even, so every answer shows
its citations and notes. **Kill condition:** below the keyword baseline, use keyword search; below
the break-even, stop.

**Time to deploy:** minutes to install, a one-off 90 MB download, about 8 seconds to index.

## 3. What went wrong, and how I fixed it

| what went wrong | how I found it | what I did | result |
|---|---|---|---|
| 25-word chunks cut procedure steps and table rows in half | reviewer feedback; a 25-300 word sweep | 200-word chunks, 50 overlap: the cheapest point on the plateau | cross-division recall 55% → 91% |
| a model with no retrieval was a rigged baseline | reviewer feedback | keyword search over the same chunks | a fair baseline, more faithful than Tanya |
| my own proposed fix, classifying the question by division first, hurt | retrieval report | dropped it | recall kept at 91%, not 45% |
| answers cited a note's bracket number or the prompt's placeholder, and declined questions the notes answered | my screen recordings | the prompt says which text is the id; code flags fake citations | every decline right (4 of 4) |
| retrieval missed a needed document on 5 of 37 questions, and Tanya answered anyway | retrieval report; answering-without-evidence count | reference-following: add up to two chunks sharing a work-order or contract id; tested on answers first | misses 5 → 1; correctness 80% → 85%; unsupported answers 3 → 1 |

Reference-following is an agent's benefit as a fixed step. Against the previous version, it cost 40% more input tokens and one faithful answer (89% → 84%); the synthetic documents share ids
by design, which flatters it.

## 4. Where it still fails

**Confabulation**, NIST's word for a fluent, confident, wrong answer. One final-run answer still came
without its needed documents, and it was wrong. The figure check catches invented numbers, dates and
ids, not an invented claim without them; a retrieval-score threshold is only a backstop (at 0.45 it
catches 2 of 6 unanswerable questions).

**Citing a document it was not given** is the new failure: the extra notes mention other documents'
codes, and the model cites those documents. All three unfaithful answers did this.
The evaluation's citation check catches every one; flagging it in the app is the next step.

Six partially answerable questions test invention directly: no answer invented the missing half,
and four said plainly that it was missing. **Hybrid search** lifts document recall from 88% to 93% alone, but adds nothing to reference-following (98% either way), so it was not adopted.

## 5. Risks and their built mitigations

All 39 cases pass in `results/guardrails.md`. OWASP numbers are the 2026 edition's, as taught.

| risk | mitigation in code |
|---|---|
| confabulation, fake citations | figure check; malformed-citation check; answering-without-evidence count |
| unanswerable questions | hand-off to a person below 0.45, no model call |
| injection in an upload (LLM01) | pattern scan sends it to a person, not the model |
| injection through a filed upload (LLM01, LLM09) | matching sentences stripped from every note before a prompt; the reader is warned |
| excessive agency (LLM03) | no tools; the only write is an upload a person confirmed |
| unbounded spend (LLM06) | a session token cap that halts |

Stripping is a tripwire, not a cure: an attacker can rephrase. An injection is survivable because
Tanya cannot send anything out, so the worst outcome is a wrong paragraph a person reads. Wrong
answers are invisible but undoable, so they are monitored across the question set and checked one
by one; the one action, filing an upload, waits for a person.

Intended use: briefing leaders on a fictional conglomerate; not live client data, automated
decisions, or judgements about people. Singapore's IMDA framework is voluntary; the PDPA is the
binding floor, which real documents would engage. The corpus is synthetic, so these numbers show
the method works, not that it transfers unchanged.
