# Tanya — business and technical trade-offs

PE6201 End-of-Course Project · Trixie Grace Mok. Every number below comes from a file in
`results/`, and every free one can be regenerated with the commands in the README.

## 1. What I chose, and what stays rules

Leaders at TGMOK Holdings need answers that combine facts from three divisions' private,
changing documents. A prompted model alone cannot do this: it has never seen the documents.
So I built retrieval-augmented generation (RAG) with citations, and I measure it against a
**non-AI baseline: keyword (TF-IDF) search over the same chunks**, not against a model with no
retrieval, which scores near zero whatever the retrieval does and so teaches nothing.

The keyword baseline is not a pushover. It retrieves every needed document more often than my
embeddings (91% against 88%), while my retrieval covers every needed *division* more often
(100% against 91%; `results/retrieval_recall.md`). On the same 20 questions
(`results/notebook_run.md`), embeddings answered 80% correctly against the baseline's 75%, but
the baseline was more faithful: 95% against 80%, below my 85% target. So embeddings earn their
place on coverage and correctness, not on faithfulness. I report that rather than hide it.

The model does three jobs: answering from cited notes, routing an upload to divisions, and
judging faithfulness (a different model family from the answerer). Everything that must be
exact stays code: the abstention phrase, the confidence hand-off, the figure check, the
fake-citation check, the token cap, the injection scan, and a person confirming every upload.
I did not build an agent: every question here is look up and synthesise, with no tool loop and
no irreversible action, so an agent would add calls and failure modes without buying anything.

## 2. Build or rent, layer by layer, and what it costs

| layer | own or rent | what, and why |
|---|---|---|
| interface | own the code, rent Streamlit | a demo leaders can use; no front-end to maintain |
| orchestration | own | Python, about 350 lines; the grounding and hand-off logic is the product |
| retrieval and vector store | own | numpy in memory: 21 chunks need no database |
| embeddings | rent open weights | `all-MiniLM-L6-v2`, run locally: no per-call price, no data leaves the laptop |
| generation | rent | `gpt-4o-mini` via OpenRouter, $0.15 / $0.60 per million tokens in / out |
| judge | rent | `gemini-2.5-flash`, evaluation only, never on a user's path |
| evaluation and observability | own | a generic tool cannot know whether an answer matches these documents |

**Cost per use** is calls x tokens x price. A question is one call of about 1,700 input tokens
(the grounded prompt plus five notes), about $0.0003; filing an upload is two calls, about
$0.0005; a question handed to a person makes no call (`results/cost_estimate.md`, estimated from
the real prompts; the live run measures it). **Time to deploy** on a new laptop: a pip install
of a few minutes, a one-off 90 MB model download, then about 8 seconds to index the 18
documents. A real deployment would add what I deliberately left out: connecting each
division's document store and its access control.

I went straight to code rather than a hosted no-code RAG builder, because I needed to measure
retrieval separately from generation, and a builder hides the retrieval step.

## 3. Trade-offs I measured, and one I had to reverse

**Chunk size.** My first plan used 25-word chunks, which cut SOP steps in half. A sweep from 25
to 300 words (`results/chunk_sweep.md`) raised cross-division recall from 82% at my earlier 60
words to 91% at 200, flat beyond that, at about three times the words sent per question (286 to
821). I chose 200 as the cheapest point on the plateau.

**Title-prefixed embedding** lifted division recall from 91% to 100% at no generation cost, so
I shipped it. But document recall did not move (88% either way), and for the hardest question
it pushed the needed CNC tooling spec from rank 6 to rank 8, the opposite of what the same
change did at 60-word chunks. I kept that reversal in the notebook as the lesson: a change is
judged on the full set every time a setting moves, never on the one case that prompted it.

**My own proposed mitigation failed.** Classifying the question by division before retrieving
cut cross-division recall from 91% to 45%, so I dropped it.

## 4. Helpful against honest: abstention, and the silent failure

A retrieval-score threshold is a weak signal here: at 0.45 it catches 2 of 6 unanswerable
questions and wrongly hands off 1 of 31 answerable ones, because plausible-but-absent questions
score like real ones. I keep it as a backstop, not the defence.

Fixing a bug found in screen recordings, where Tanya cited a bracket number or the prompt's
placeholder instead of a document id, made it answer more: it stopped declining two questions
it could answer. The price showed in the final run. Every decline was right (4 of 4: three out
of scope, one whose evidence was never retrieved), but three questions were answered although
their needed documents were not retrieved, one of them wrongly, and an earlier run caught it
inventing a component from an unrelated document. That is the silent failure: fluent, cited,
wrong. No threshold separates those answers from good ones.

This is a business question. A wrong answer costs a person about 15 minutes to catch and redo
(an assumption, $10), roughly 30,000 times the model cost of the question. So at the measured
80% correctness the cost per *successful* answer is about $2.00 against $0.0003 at 100%: $400
against $0.06 a month at 200 questions. That is still far below the roughly $5,500 a month of
manual synthesis it shortens, but the number to watch is the failure rate, not the token bill.

## 5. Risks, each with its built mitigation

| risk | mitigation (code, tested in `results/guardrails.md`) |
|---|---|
| silent failure, OWASP LLM09 | figure check against cited documents; a silent-failure count (3 in `results/notebook_run.md`) |
| fake citations | malformed-citation check; the final run's out-of-scope declines cite nothing, not a fake id |
| unanswerable questions | hand-off to a person below 0.45, with no model call |
| instructions hidden in an upload, LLM01 | pattern scan routes it to a person; no false positives on the 18 documents (the checklist also caught and fixed a regex bug) |
| unbounded spend, LLM10 | a hard session token cap |

The residual risk is an invented claim with no number in it, which the figure check cannot
see. My next step would be the same check for named components, but only once it is validated
on the full set.

Intended use: briefing leaders on a fictional conglomerate. Not for live financial or client
data, automated decisions, or inferences about people. A person reviews every answer, in line
with the human-oversight principle of Singapore's IMDA Model AI Governance Framework. The
corpus is synthetic, so these numbers show the method works, not that it transfers unchanged
to messier real documents.
