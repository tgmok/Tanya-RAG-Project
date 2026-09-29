"""Cost to serve, in the three-layer shape of the course's cost calculator (Class 5):

    layer 1  variable per question   = calls x (input tokens x price + output tokens x price)
                                       + a person checking the answer against its notes (every answer)
    layer 2  expected fallback       = (1 - success rate) x cost of a person redoing the answer by hand
    cost per successful answer       = layer 1 + layer 2
    layer 3  fixed monthly           = hosting, upkeep, evaluation re-runs (config.FIXED_MONTHLY_USD)
    monthly                          = cost per successful answer x volume + layer 3
    break-even success rate          = the rate at which Tanya costs the same as answering by hand:
                                       p = 1 - (manual - layer 1) / redo cost    (the course's formula)

    python cost_model.py --estimate   free, no key: prices the ACTUAL prompts the shipped system and
                                      the keyword baseline send, and times the one-off setup
                                      (time-to-deploy)                    -> results/cost_estimate.md
    python cost_model.py              after `python run_eval.py --run`: measured tokens and
                                      measured pass rates                 -> results/cost_model.md

Prices and cost-model assumptions live in config.py (one dated block). Serving cost counts only
the generation model: embeddings run locally (no per-call price) and the judge is an evaluation
instrument, not part of answering a user, so its cost is reported separately.
"""
import argparse
import importlib
import json
import sys
import time
from datetime import date

from config import (ANALYST_USD_PER_HOUR, CHARS_PER_TOKEN, CHECK_MINUTES, CYCLES_PER_MONTH, DATA_DIR,
                    EST_ANSWER_TOKENS, FIXED_MONTHLY_USD, GEN_MODEL, HOURS_PER_DAY, HUMAN_REVIEW_MINUTES,
                    MANUAL_CYCLE_DAYS, MEASURED_CORRECTNESS, PRICES, PRICES_DATED, RESULTS_DIR, VOLUMES)


def variable_cost(model, tokens_in, tokens_out):
    p = PRICES[model]
    return tokens_in / 1e6 * p["in"] + tokens_out / 1e6 * p["out"]


def failure_cost_usd():
    """A person redoing a wrong or declined answer by hand."""
    return ANALYST_USD_PER_HOUR * HUMAN_REVIEW_MINUTES / 60.0


def manual_per_question_usd():
    """The no-AI alternative: a person answering the question from the documents. The same work as a
    redo, so the same price."""
    return failure_cost_usd()


def check_cost_usd(minutes=CHECK_MINUTES):
    """A person reading an answer against its cited notes before using it. Paid on EVERY answer, right
    or wrong: the human-in-the-loop gate is not free just because it is a good idea."""
    return ANALYST_USD_PER_HOUR * minutes / 60.0


def fixed_monthly_usd():
    return sum(FIXED_MONTHLY_USD.values())


def cost_per_successful(model_usd, success_rate, check_usd=None):
    """Layer 1 (model + the check) + layer 2 (expected redo)."""
    assert 0.0 <= success_rate <= 1.0
    check_usd = check_cost_usd() if check_usd is None else check_usd
    return model_usd + check_usd + (1.0 - success_rate) * failure_cost_usd()


def break_even_success_rate(cheap_var, dear_total, failure_usd):
    """The course's formula (Class 5 calculator): the success rate at which the cheap option costs
    the same as the dear one.  cheap_var + (1-p) * failure = dear_total."""
    return max(0.0, min(1.0, 1.0 - (dear_total - cheap_var) / failure_usd))


def tanya_break_even(model_usd, check_usd=None):
    """Below this success rate, answering by hand is cheaper than Tanya."""
    check_usd = check_cost_usd() if check_usd is None else check_usd
    return break_even_success_rate(model_usd + check_usd, manual_per_question_usd(), failure_cost_usd())


def monthly(per_success_usd, volume, fixed=True):
    return per_success_usd * volume + (fixed_monthly_usd() if fixed else 0.0)


def manual_monthly_usd():
    return MANUAL_CYCLE_DAYS * HOURS_PER_DAY * ANALYST_USD_PER_HOUR * CYCLES_PER_MONTH


def est_tokens(text):
    return len(text) / CHARS_PER_TOKEN


def economics_section(model_usd, success, baseline_success=None, source=""):
    """The part of the cost that is people: the check on every answer, the expected redo, the break-even
    against answering by hand, layer 3, and the kill condition. Shared by the estimate and the measured
    report so the two cannot price people differently."""
    chk, redo = check_cost_usd(), failure_cost_usd()
    be = tanya_break_even(model_usd)
    L = ["## Layer 1, continued: a person checks every answer", "",
         f"Every answer is a draft that a person reads against its cited notes before using it: {CHECK_MINUTES} "
         f"minutes at ${ANALYST_USD_PER_HOUR:.0f}/h = ${chk:.2f} (an ASSUMPTION in config.py), about "
         f"{chk / model_usd:,.0f}x the model cost of the question. This is the human-in-the-loop gate, priced: "
         "it is paid on right answers too.", "",
         "## Layer 2 and the break-even against answering by hand", "",
         f"A wrong or declined answer is redone by hand: {HUMAN_REVIEW_MINUTES} minutes = ${redo:.2f}, the same "
         "work as answering the question without Tanya, the no-AI alternative. The course's break-even, "
         f"p = 1 - (manual - layer 1) / redo, puts it at **{be:.0%}**: Tanya is cheaper than answering by hand "
         f"whenever more than {be:.0%} of its answers are right."]
    if success is not None:
        slack = (manual_per_question_usd() - model_usd - (1 - success) * redo) / (ANALYST_USD_PER_HOUR / 60.0)
        L += ["", f"Measured: {success:.0%} ({source}), {success / be:.0f} times the break-even, so the decision "
              f"is robust rather than a knife-edge. At {success:.0%}, checking an answer could take up to "
              f"{slack:.0f} minutes before answering by hand became cheaper."]
    L += ["", "The break-even moves with the minutes the check takes, far more than with anything the model "
          "costs, which is why every answer carries its citations and the notes it drew on: they are what keep "
          "the check short.", "", "| minutes to check one answer | break-even success rate |", "|---|---|"]
    for m in (1, CHECK_MINUTES, 5, 10, HUMAN_REVIEW_MINUTES):
        L.append(f"| {m}{' (assumed)' if m == CHECK_MINUTES else ''} | "
                 f"{tanya_break_even(model_usd, check_cost_usd(m)):.0%} |")
    L += ["", "## Layer 3: fixed monthly, and the month in total", "",
          "| fixed cost (ASSUMPTIONS, config.py) | $ per month |", "|---|---|"]
    L += [f"| {k} | ${v:,.2f} |" for k, v in FIXED_MONTHLY_USD.items()]
    L += [f"| **total** | **${fixed_monthly_usd():,.2f}** |", "",
          "| answer success rate | cost per successful answer | " +
          " | ".join(f"month at {v:,} questions" for v in VOLUMES) + " |", "|---|---|" + "---|" * len(VOLUMES)]
    for pr in sorted({1.00, 0.90, success or 0.80, 0.70, 0.50}, reverse=True):
        ps = cost_per_successful(model_usd, pr)
        mark = " (measured)" if success is not None and abs(pr - success) < 1e-9 else ""
        L.append(f"| {pr:.0%}{mark} | ${ps:.2f} | " + " | ".join(f"${monthly(ps, v):,.0f}" for v in VOLUMES) + " |")
    L.append("| answering every question by hand | $" + f"{manual_per_question_usd():.2f} | "
             + " | ".join(f"${manual_per_question_usd() * v:,.0f}" for v in VOLUMES) + " |")
    per_at = cost_per_successful(model_usd, success if success is not None else 0.80)
    min_volume = fixed_monthly_usd() / max(1e-9, manual_per_question_usd() - per_at)
    L += ["", "Layer 3 is spread over more questions as volume grows, so the case for Tanya strengthens with "
          "volume; the check and the redo never amortise. Below about "
          f"{min_volume:.0f} questions a month, the fixed cost alone makes answering by hand cheaper.", "",
          "## Kill condition, written before a pilot", "",
          "Class 5's last gate: capture the baseline now and write down what would make us stop. Re-run the "
          "fixed 20-question set after every change, and:", "",
          f"1. if answer correctness falls below the keyword baseline's"
          + (f" ({baseline_success:.0%} in the same run)" if baseline_success is not None else "")
          + ", switch to keyword retrieval: it is simpler, needs no embedding model, and on that result it won;",
          f"2. if it falls below the {be:.0%} break-even, or reviewers report the check taking longer than it "
          "would take to answer by hand, stop and answer by hand."]
    return L


def estimate_run(gen_model, judge_model, n_questions, n_scored, configs, do_judge=True,
                 words_sent=None, no_retrieval_floor=False):
    """Rough UPPER-bound dollars for a live evaluation run, printed before anything is spent.
    words_sent: {config: average words of notes sent}, measured by the free retrieval report in the
    same run, so the estimate tracks the real chunk size. None if a model has no price."""
    if gen_model not in PRICES or (do_judge and judge_model not in PRICES):
        return None
    words_sent = words_sent or {}
    total = n_questions * variable_cost(gen_model, 60, 100) if no_retrieval_floor else 0.0
    for c in configs:
        tin = words_sent.get(c, 1200) * 1.4 + 250          # ~1.4 tokens/word + system prompt
        total += n_questions * variable_cost(gen_model, tin, 150)
        if do_judge:
            total += n_scored * variable_cost(judge_model, tin + 500, 700)  # judge models may 'think'
    return total


# ---------------------------------------------------------------------------
# --estimate: free, before any live run
# ---------------------------------------------------------------------------

def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def run_estimate():
    import harness as H
    import rag_core
    import doc_parser

    t_start = time.perf_counter()
    importlib.import_module("sentence_transformers")  # timed: the heaviest import in the stack
    t_import = time.perf_counter() - t_start
    idx, t_index = _timed(H.build_indexes)
    using = idx["plain"]["embedder"].using
    main = [q for q in H.load_questions(include_extra=False, include_independent=False)
            if q["kind"] != "out_of_scope"]

    def prompt_tokens(config):
        """(average whole-prompt tokens, average tokens per retrieved note) over the 20 questions."""
        whole, per_note = [], []
        for q in main:
            hits = H.retrieve_config(config, q["question"], idx)
            context = rag_core.format_notes(hits)
            user = f"NOTES:\n{context}\n\nQUESTION: {q['question']}"
            whole.append(est_tokens(rag_core.GROUNDED) + est_tokens(user))
            per_note.append(est_tokens(context) / max(1, len(hits)))
        return sum(whole) / len(whole), sum(per_note) / len(per_note)

    measured = {c: prompt_tokens(c) for c in (H.SHIPPED, H.BASELINE, "full_context")}
    ask = {c: m[0] for c, m in measured.items()}
    note_tokens = measured[H.SHIPPED][1]

    # Filing an upload is two calls: classify the raw text, then the cross-division impact brief.
    sample = DATA_DIR / "sample_uploads" / "meadowfield_snacks_onboarding.docx"
    up_text = doc_parser.extract_text(sample.name, sample.read_bytes())
    t_classify_in = est_tokens(rag_core.CLASSIFY_SYSTEM) + est_tokens(up_text[:6000])
    # the brief sends the upload's opening 400 characters plus 4 retrieved notes (k=4 in rag_core)
    t_brief_in = est_tokens(rag_core.IMPACT_SYSTEM) + est_tokens(up_text[:400]) + 4 * note_tokens

    g = GEN_MODEL
    per_q = {c: variable_cost(g, t, EST_ANSWER_TOKENS) for c, t in ask.items()}
    per_upload = variable_cost(g, t_classify_in, 60) + variable_cost(g, t_brief_in, 250)

    L = ["# Cost to serve and time to deploy: the estimate before any live run", "",
         f"Written by `python cost_model.py --estimate` on {date.today()}. Free: no key, no model call.",
         f"Generation model `{g}` at ${PRICES[g]['in']}/1M in, ${PRICES[g]['out']}/1M out "
         f"(prices dated {PRICES_DATED}; source: {PRICES[g]['source']}).", "",
         "**Input tokens are ESTIMATED** from the actual prompts: the grounded system prompt plus the notes "
         f"each config really retrieves for the 20 scored questions, at {CHARS_PER_TOKEN} characters per token. "
         f"**Output tokens are ASSUMED** ({EST_ANSWER_TOKENS} per answer). `python run_eval.py --run` "
         "replaces both with the API's own usage counts, and `python cost_model.py` then writes "
         "`results/cost_model.md` from those.", "",
         "## Layer 1: calls x tokens x price", "",
         "| user action | model calls | input tokens (est.) | output tokens (assumed) | $ per action |",
         "|---|---|---|---|---|",
         f"| ask a question: `{H.SHIPPED}` (what the app ships) | 1 | {ask[H.SHIPPED]:,.0f} | "
         f"{EST_ANSWER_TOKENS} | ${per_q[H.SHIPPED]:.5f} |",
         f"| ask a question: `{H.BASELINE}` (the keyword baseline) | 1 | {ask[H.BASELINE]:,.0f} | "
         f"{EST_ANSWER_TOKENS} | ${per_q[H.BASELINE]:.5f} |",
         f"| ask a question: `full_context` (all 18 documents in the prompt, no retrieval) | 1 | "
         f"{ask['full_context']:,.0f} | {EST_ANSWER_TOKENS} | ${per_q['full_context']:.5f} |",
         f"| file an upload (classify + impact brief) | 2 | {t_classify_in + t_brief_in:,.0f} | 310 | "
         f"${per_upload:.5f} |",
         "", "A question the shipped system hands to a person below the confidence threshold makes "
         "**zero** model calls. Embedding is local and free per call.", "",
         f"**Retrieval against long context.** At 18 documents the whole corpus fits in one prompt, which is "
         f"Class 2's rule for skipping retrieval, and it costs only {ask['full_context'] / ask[H.SHIPPED]:.1f}x "
         "the tokens of the shipped retrieval. That is the honest case for long context here. Retrieval is chosen "
         "for what the pilot stands for: every division's documents over years will not fit, the long-context "
         "cost grows with the corpus while retrieval does not, and retrieval is where a real deployment would "
         "enforce which division's documents a reader may see.", ""]
    L += economics_section(per_q[H.SHIPPED], MEASURED_CORRECTNESS.get(H.SHIPPED),
                           MEASURED_CORRECTNESS.get(H.BASELINE),
                           "answer correctness in the final evaluation run, `results/summary.md`")
    L += ["", "## Context: the weekly report", "",
          f"The problem statement puts cross-division synthesis at 3-5 business days per weekly cycle, about "
          f"${manual_monthly_usd():,.0f}/month of analyst time at these assumptions. That is context, not a "
          "like-for-like saving: Tanya answers questions, it does not replace the report.", "",
          "## Time to deploy, measured on this machine", "",
          f"Embedder: {using}.", "",
          "| step | time | notes |", "|---|---|---|",
          "| `pip install -r requirements.txt` | minutes | one-off; dominated by torch (CPU build) |",
          "| first embedding-model download | one-off, ~90 MB | cached by sentence-transformers after that |",
          f"| import the embedding stack | {t_import:.1f} s | measured |",
          f"| load the model and index 18 documents (3 indexes: plain, titled, keyword) | {t_index:.1f} s | "
          "measured; the app builds 1 index, once per session |",
          "| add one document through the app | about 2 model calls + one re-index | measured index time above |",
          "", "What it would take for real (an estimate, not measured): connecting each division's document "
          "store and its access control, which this project deliberately does not do (fictional corpus). "
          "Code-wise the retrieval is domain-agnostic: point `config.DOC_ID_TO_PATH` at other documents and "
          "re-run `python data/check_my_data.py`.", ""]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "cost_estimate.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nwritten: {RESULTS_DIR / 'cost_estimate.md'}")


# ---------------------------------------------------------------------------
# Measured: after a live run
# ---------------------------------------------------------------------------

def run_measured():
    summary_path = RESULTS_DIR / "summary.json"
    if not summary_path.exists():
        print("results/summary.json not found. Run `python run_eval.py --run` first, or "
              "`python cost_model.py --estimate` for the free estimate.")
        sys.exit(1)
    s = json.loads(summary_path.read_text(encoding="utf-8"))
    gen = s["gen_model"]
    if gen not in PRICES:
        print(f"No price for {gen}; add it to PRICES in config.py first.")
        sys.exit(1)

    lines = ["# Cost to serve: what one answer costs (measured)", "",
             f"Generation model: `{gen}`. Prices dated {PRICES_DATED} "
             f"(in {PRICES[gen]['in']}/1M, out {PRICES[gen]['out']}/1M; source: {PRICES[gen]['source']}).",
             "Tokens and pass rates are MEASURED (results/summary.json, the API's own usage counts). "
             "Labour numbers are ASSUMPTIONS (config.py). Success = the answer contains its key facts "
             "(answer correctness), main set only.", "",
             "| config | avg tokens in/out | model $/question | + check | answer correctness | "
             "cost per successful answer | break-even vs by hand |",
             "|---|---|---|---|---|---|---|"]
    succ_of, var_of = {}, {}
    for name, agg in s["configs"].items():
        var = variable_cost(gen, agg["avg_tokens_in"], agg["avg_tokens_out"])
        main_agg = s.get("by_set", {}).get("configs", {}).get(name, {}).get("main", agg)
        succ = main_agg["key_fact_pass"] or 0.0
        succ_of[name], var_of[name] = succ, var
        lines.append(f"| {name} | {agg['avg_tokens_in']:.0f} / {agg['avg_tokens_out']:.0f} | ${var:.5f} | "
                     f"${check_cost_usd():.2f} | {succ:.0%} | ${cost_per_successful(var, succ):.2f} | "
                     f"{tanya_break_even(var):.0%} |")
    ship = s.get("shipped_config", "shipped")
    if ship in var_of:
        lines += [""] + economics_section(var_of[ship], succ_of[ship], succ_of.get(s.get("baseline_config")),
                                          "answer correctness in this run, main set")
    lines += ["", "## Context: the weekly report", "",
              f"The problem statement puts cross-division synthesis at 3-5 business days per report cycle. At "
              f"{MANUAL_CYCLE_DAYS} days x {HOURS_PER_DAY} h x ${ANALYST_USD_PER_HOUR:.0f}/h x {CYCLES_PER_MONTH} "
              f"cycles/month that is about ${manual_monthly_usd():,.0f}/month of analyst time. This is context, "
              "not a like-for-like saving: Tanya answers questions, it does not replace the report.", ""]

    if s.get("judge_model") and s["judge_model"] in PRICES:
        jc = sum(variable_cost(s["judge_model"], a["judge_tokens_in"], a["judge_tokens_out"])
                 for a in s["configs"].values())
        lines += [f"Judge (`{s['judge_model']}`) cost for this whole evaluation run: about ${jc:.3f}. "
                  "Evaluation cost only; not part of serving a user.", ""]

    (RESULTS_DIR / "cost_model.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten: {RESULTS_DIR / 'cost_model.md'}   (as of {date.today()})")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--estimate", action="store_true", help="free: price the real prompts, time the setup")
    args = ap.parse_args()
    run_estimate() if args.estimate else run_measured()


if __name__ == "__main__":
    main()
