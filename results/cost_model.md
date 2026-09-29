# Cost to serve: what one answer costs (measured)

Generation model: `openai/gpt-4o-mini`. Prices dated 2026-09-21 (in 0.15/1M, out 0.6/1M; source: A1 Part 1 notebook (OpenRouter list price)).
Tokens and pass rates are MEASURED (results/summary.json, the API's own usage counts). Labour numbers are ASSUMPTIONS (config.py). Success = the answer contains its key facts (answer correctness), main set only.

| config | avg tokens in/out | model $/question | + check | answer correctness | cost per successful answer | break-even vs by hand |
|---|---|---|---|---|---|---|
| shipped | 1402 / 56 | $0.00024 | $2.00 | 80% | $4.00 | 20% |
| tfidf_k5 | 1608 / 56 | $0.00027 | $2.00 | 75% | $4.50 | 20% |

## Layer 1, continued: a person checks every answer

Every answer is a draft that a person reads against its cited notes before using it: 3 minutes at $40/h = $2.00 (an ASSUMPTION in config.py), about 8,194x the model cost of the question. This is the human-in-the-loop gate, priced: it is paid on right answers too.

## Layer 2 and the break-even against answering by hand

A wrong or declined answer is redone by hand: 15 minutes = $10.00, the same work as answering the question without Tanya, the no-AI alternative. The course's break-even, p = 1 - (manual - layer 1) / redo, puts it at **20%**: Tanya is cheaper than answering by hand whenever more than 20% of its answers are right.

Measured: 80% (answer correctness in this run, main set), 4 times the break-even, so the decision is robust rather than a knife-edge. At 80%, checking an answer could take up to 12 minutes before answering by hand became cheaper.

The break-even moves with the minutes the check takes, far more than with anything the model costs, which is why every answer carries its citations and the notes it drew on: they are what keep the check short.

| minutes to check one answer | break-even success rate |
|---|---|
| 1 | 7% |
| 3 (assumed) | 20% |
| 5 | 33% |
| 10 | 67% |
| 15 | 100% |

## Layer 3: fixed monthly, and the month in total

| fixed cost (ASSUMPTIONS, config.py) | $ per month |
|---|---|
| hosting: one small cloud VM for the Streamlit app | $20.00 |
| upkeep: 4 hours a month re-running the free checks and updating documents | $160.00 |
| re-running the answer-level evaluation after each change, about 4 a month | $1.00 |
| **total** | **$181.00** |

| answer success rate | cost per successful answer | month at 200 questions | month at 2,000 questions |
|---|---|---|---|
| 100% | $2.00 | $581 | $4,181 |
| 90% | $3.00 | $781 | $6,181 |
| 80% (measured) | $4.00 | $981 | $8,181 |
| 70% | $5.00 | $1,181 | $10,181 |
| 50% | $7.00 | $1,581 | $14,181 |
| answering every question by hand | $10.00 | $2,000 | $20,000 |

Layer 3 is spread over more questions as volume grows, so the case for Tanya strengthens with volume; the check and the redo never amortise. Below about 30 questions a month, the fixed cost alone makes answering by hand cheaper.

## Kill condition, written before a pilot

Class 5's last gate: capture the baseline now and write down what would make us stop. Re-run the fixed 20-question set after every change, and:

1. if answer correctness falls below the keyword baseline's (75% in the same run), switch to keyword retrieval: it is simpler, needs no embedding model, and on that result it won;
2. if it falls below the 20% break-even, or reviewers report the check taking longer than it would take to answer by hand, stop and answer by hand.

## Context: the weekly report

The problem statement puts cross-division synthesis at 3-5 business days per report cycle. At 4 days x 8 h x $40/h x 4.33 cycles/month that is about $5,542/month of analyst time. This is context, not a like-for-like saving: Tanya answers questions, it does not replace the report.

Judge (`google/gemini-2.5-flash`) cost for this whole evaluation run: about $0.042. Evaluation cost only; not part of serving a user.
