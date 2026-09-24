"""Run Tanya's evaluation. This is the entry point a marker runs.

    python run_eval.py --retrieval-only     free, no API key: recall for every retrieval config
    python run_eval.py --chunk-sweep        free: why 200-word chunks
    python run_eval.py --leakage            free: does a question already contain its own answer?
    python run_eval.py --dry-run            free: the whole live path with a fake model -> results/_dryrun/
    python run_eval.py --run                live: the shipped system against the keyword baseline on the
                                            same questions -- answer correctness, faithfulness (judge),
                                            abstention, the silent-failure count, citations, tokens
    python run_eval.py --agreement          after you hand-grade results/judge_spotcheck.json

--run prints an estimated cost and asks before spending anything (use --yes to skip the prompt).
The API key is read from OPENROUTER_API_KEY or MY_PRIVATE_OPENROUTER_KEY, else asked for with a
hidden prompt. It is never written to disk.
"""
import argparse
import getpass
import json
import os
import sys
from datetime import date

import config as cfg
import cost_model
import harness as H


def fmt(x, pct=True):
    if x is None:
        return "n/a"
    return f"{x:.0%}" if pct else f"{x:.2f}"


def write_retrieval_report(out_dir, questions, idx):
    per_config = {}
    for config in H.CONFIGS:
        recs = [H.recall_for_question(q, config, idx) for q in questions if q["kind"] != "out_of_scope"]
        per_config[config] = {"records": recs,
                              "main": H.summarise_recall([r for r in recs if r["set"] == "main"]),
                              "all": H.summarise_recall(recs)}

    L = ["# Retrieval recall by configuration (no model, no cost)", "",
         f"Embedder: {idx['plain']['embedder'].using}. Chunking: {cfg.CHUNK_WORDS} words, overlap "
         f"{cfg.OVERLAP}. Fixed corpus only (18 documents, {len(idx['plain']['chunks'])} chunks).", "",
         f"`{H.SHIPPED}` is exactly what the app runs. `{H.BASELINE}` is THE baseline: keyword search over the "
         "same chunks, a non-AI method, so the comparison asks whether embeddings earn their complexity.", "",
         "Division recall = the retrieved chunks cover EVERY division the question needs (Section 7's "
         "context-recall metric). Doc recall = share of the needed documents retrieved. "
         "Target for cross-division division recall: 80%.", "",
         "Caveat: `balanced_2x3` and `full_context` cover every division by construction, so their division recall "
         "is 100% by design and shows nothing about choosing the right documents. Compare avg doc recall, words sent, and the "
         "answer-level results from --run, instead.", "",
         "| config | cross-division recall (main 11) | all scored (main 20) | avg doc recall | avg items sent | avg words sent |",
         "|---|---|---|---|---|---|"]
    for config, d in per_config.items():
        m = d["main"]
        L.append(f"| `{config}`: {H.CONFIGS[config]['label']} | {fmt(m['division_recall_cross'])} | "
                 f"{fmt(m['division_recall_all'])} | {fmt(m['avg_doc_recall'])} | {m['avg_chunks']:.1f} | {m['avg_words']:.0f} |")

    for config, d in per_config.items():
        misses = [r for r in d["records"] if r["diagnosis"]]
        L += ["", f"## Misses under `{config}` ({len(misses)} questions missing at least one needed document)", ""]
        if not misses:
            L.append("None.")
        for r in misses:
            L.append(f"- **{r['id']}** ({r['kind']}, {r['set']}); retrieved {r['retrieved']}")
            for dg in r["diagnosis"]:
                L.append(f"  - `{dg['missing_doc']}`: best chunk ranked #{dg['best_chunk_rank']} of "
                         f"{len(idx['plain']['chunks'])} at score {dg['best_chunk_score']}, versus a retrieval cutoff of "
                         f"{dg['retrieval_cutoff_score']}")
    curve, dist = H.abstention_curve(questions, idx)
    L += ["", "## Abstain below a retrieval score? (Section 8's confidence threshold; free, no model)", "",
          f"Best retrieval score under `{H.SHIPPED}` -- the scores the app's threshold actually sees. Answerable questions: minimum {dist['answerable_min']:.3f}, median "
          f"{dist['answerable_median']:.3f}. Questions the corpus cannot answer: "
          + ", ".join(f"{s_:.3f}" for s_ in dist["absent"]) + ".", "",
          "| abstain below | unanswerable caught | answerable wrongly refused |", "|---|---|---|"]
    for r in curve:
        L.append(f"| {r['threshold']:.2f} | {r['absent_caught']}/{r['n_absent']} | {r['answerable_lost']}/{r['n_answerable']} |")
    L += ["", "Reading it: the unanswerable questions here are deliberately plausible, so their scores overlap the "
          "answerable ones. A threshold is a weak backstop, not a substitute for the grounded prompt and the "
          "citation check. The thresholds are judged on the same questions they were chosen from, so this is optimistic.", ""]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "retrieval_recall.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out_dir / "retrieval_recall.json").write_text(json.dumps(
        {c: {"main": d["main"], "all": d["all"], "records": d["records"]} for c, d in per_config.items()},
        indent=2), encoding="utf-8")
    return per_config, "\n".join(L)


KEY_FILE = cfg.KEY_FILE   # untracked, see .gitignore


def load_key(key_file=KEY_FILE):
    """Return (key, where_it_came_from) without ever printing the key.
    Order: environment variable, then the untracked OpenRouter_api.txt in the project root."""
    for var in ("OPENROUTER_API_KEY", "MY_PRIVATE_OPENROUTER_KEY"):
        if os.environ.get(var):
            return os.environ[var].strip(), f"environment variable {var}"
    if key_file.exists():
        for line in key_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line, key_file.name
    return None, None


def run_chunk_sweep(out_dir, questions):
    """Free (no model). Why 200/50 rather than the 25/10 in the problem statement's smallest slice?
    Extended per reviewer feedback on the problem statement (25/10 will cut an SOP step or a table
    row in half) to also cover 150-300 words -- documents here are 150-300 words each, so 300 is
    close to one whole document per chunk, the comparison point the notebook's own markdown names."""
    print("Building indexes for each chunk size (loads the embedding model once)...")
    base = H.build_index()
    sizes = [(25, 10), (40, 10), (60, 15), (100, 25), (150, 40), (200, 50), (250, 60), (300, 75)]
    scored_q = [q for q in questions if q["kind"] != "out_of_scope"]
    L = ["# Chunk-size sweep (no model, no cost)", "",
         f"Embedder: {base['embedder'].using}. Fixed corpus, {len(scored_q)} answerable questions from every set; "
         "cross-division column uses the main set's 11 cross-division questions. The problem statement's smallest "
         "slice used 25 words with 10 overlap; the notebook and app now use 200 with 50.", "",
         "| chunk / overlap | chunks | top-k | cross-division recall | avg doc recall | avg words sent |", "|---|---|---|---|---|---|"]
    for cw, ov in sizes:
        idx = {"plain": H.build_index(embedder=base["embedder"], chunk_words=cw, overlap=ov)}
        for config in ("naive_k3", "naive_k5"):
            recs = [H.recall_for_question(q, config, idx) for q in scored_q]
            main = H.summarise_recall([r for r in recs if r["set"] == "main"])
            allr = H.summarise_recall(recs)
            L.append(f"| {cw} / {ov} | {len(idx['plain']['chunks'])} | {H.CONFIGS[config]['k']} | "
                     f"{fmt(main['division_recall_cross'])} | {fmt(allr['avg_doc_recall'])} | {allr['avg_words']:.0f} |")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chunk_sweep.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def run_leakage(out_dir, questions):
    """Free (no model). Watch-outs section 6: does the input already contain the answer?
    Report the score before and after stripping it."""
    print("Building index (loads the embedding model)...")
    idx = H.build_indexes()
    rows, s_ = H.leakage_check(questions, idx)
    L = ["# Leakage check (no model, no cost)", "",
         "Does the question already contain the answer it is graded on? Two kinds are checked: "
         "**question-side** (a key fact the answer is scored on is already stated in the question, so "
         "`key_fact_check` could pass on the asker's words) and **retrieval-side** (the question repeats "
         "the source document's wording, so retrieval is string matching). For every leaky question the "
         "leaked phrases are deleted and recall is re-scored -- the before/after gap is what those copied "
         "words were carrying.", "",
         f"Config: `{H.SHIPPED}`. Scored questions examined: {s_['n_questions']}. "
         f"With at least one leaked key fact: **{s_['n_with_leakage']}** ({fmt(s_['share_with_leakage'])}).", ""]
    if s_["n_with_leakage"]:
        L += [f"On the leaky questions only, document recall {fmt(s_['doc_recall_before'])} before stripping "
              f"-> {fmt(s_['doc_recall_after'])} after; division recall {fmt(s_['division_recall_before'])} "
              f"-> {fmt(s_['division_recall_after'])}.",
              f"Across all scored questions, document recall {fmt(s_['all_doc_recall_before'])} -> "
              f"{fmt(s_['all_doc_recall_after'])}.", "",
              "| id | set | leaked groups / total | leaked phrases | doc recall before -> after | division recall before -> after |",
              "|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: -r["n_leaked_groups"]):
            if not r["n_leaked_groups"]:
                continue
            L.append(f"| {r['id']} | {r['set']} | {r['n_leaked_groups']}/{r['n_facts']} | "
                     f"{', '.join('`' + x + '`' for x in r['leaked'])} | "
                     f"{fmt(r['doc_recall_before'])} -> {fmt(r['doc_recall_after'])} | "
                     f"{r['division_recall_before']} -> {r['division_recall_after']} |")
        L += ["", "Stripped questions, for inspection:", ""]
        for r in rows:
            if r["n_leaked_groups"]:
                L.append(f"- **{r['id']}**: `{r['question_stripped']}`")
    else:
        L.append("No question states any of the key facts its answer is graded on. Nothing to strip.")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "leakage.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


def get_client(dry_run):
    if dry_run:
        return H.FakeClient()
    from openai import OpenAI
    key, source = load_key()
    if key:
        print(f"Using the OpenRouter key from {source}.")
    else:
        key = getpass.getpass("Paste your OpenRouter API key (hidden): ").strip()
    if not key.isascii() or any(c.isspace() for c in key):
        sys.exit("The key contains spaces or non-ASCII characters (an em dash, a stray label, a smart quote). "
                 "It must be only the key itself, on one line. Nothing was spent.")
    return OpenAI(base_url=cfg.BASE_URL, api_key=key)


def write_eval_report(out_dir, summary, results):
    g = summary["gen_model"]
    by_set = summary.get("by_set", {}).get("configs", {})

    def main_of(c):
        return by_set.get(c, {}).get("main", summary["configs"][c])

    L = ["# Answer-level evaluation", "",
         f"Generation `{g}`; judge `{summary['judge_model'] or 'not run'}` (a different model family from "
         f"the generator). Run {summary['date']}. Embedder: {summary.get('embedder', 'n/a')}.", ""]

    # ---- the headline: shipped vs THE baseline, the same 20 questions -------------------------
    ship, base = H.SHIPPED, H.BASELINE
    if ship in summary["configs"] and base in summary["configs"]:
        S, B = main_of(ship), main_of(base)

        def delta(k):
            if S.get(k) is None or B.get(k) is None:
                return "n/a"
            return f"{(S[k] - B[k]) * 100:+.0f} pts"

        L += ["## Headline: the shipped system against the keyword baseline", "",
              "The same main-set questions (20 scored + 3 out-of-scope, fixed before anything ran) through "
              f"`{ship}` (exactly what the app runs) and `{base}` (keyword search over the same chunks, "
              "non-AI retrieval). A no-retrieval model is NOT the baseline: it has never seen these fictional "
              "documents, so it scores near zero and teaches nothing.", "",
              "| measure | what it asks | shipped | keyword baseline | difference |",
              "|---|---|---|---|---|",
              f"| **answer correctness** | every key fact present (code check, eval_key_facts.json) | "
              f"{fmt(S['key_fact_pass'])} | {fmt(B['key_fact_pass'])} | {delta('key_fact_pass')} |",
              f"| correctness, cross-division only | the questions this project exists for | "
              f"{fmt(S['key_fact_pass_cross'])} | {fmt(B['key_fact_pass_cross'])} | {delta('key_fact_pass_cross')} |",
              f"| **faithfulness** | every claim supported by the notes (judge; target 85%) | "
              f"{fmt(S['judge_faithful'])} (n={S['judge_n']}) | {fmt(B['judge_faithful'])} (n={B['judge_n']}) | "
              f"{delta('judge_faithful')} |",
              f"| declined | said 'The documents do not say', or handed to a person | {fmt(S['declined'])} | "
              f"{fmt(B['declined'])} | {delta('declined')} |",
              f"| declines that were right | out of scope, or the needed documents were not retrieved | "
              f"{fmt(S['declines_right'])} (n={S['declines_judged']}) | {fmt(B['declines_right'])} "
              f"(n={B['declines_judged']}) | |",
              f"| **silent failures** | answered although the needed documents were NOT retrieved | "
              f"{S['answered_without_evidence_n']} ({S['answered_without_evidence_wrong']} of them wrong) | "
              f"{B['answered_without_evidence_n']} ({B['answered_without_evidence_wrong']} wrong) | |",
              f"| out-of-scope declined | the 3 questions the corpus cannot answer | {fmt(S['oos_correct'])} | "
              f"{fmt(B['oos_correct'])} | |",
              f"| figures found in cited docs | every number, date and id is in a cited document | "
              f"{fmt(S['figures_supported'])} | {fmt(B['figures_supported'])} | |",
              f"| handed to a person | retrieval score below {cfg.ABSTAIN_BELOW}, no model call | "
              f"{fmt(S['handoff'])} | {fmt(B['handoff'])} | |", "",
              "Why both correctness and faithfulness: faithfulness alone is won by quoting a chunk back, and "
              "correctness alone cannot tell a grounded answer from a lucky one. The two abstention rows are "
              "the numbers the brief asks for: how often it declines, and whether the declines were the "
              "questions it would have got wrong.", ""]

    # ---- every config -------------------------------------------------------------------------
    L += ["## Every configuration, main set", "",
          "| system | answer correctness | cross-division | faithfulness (judge) | declined | declines right | "
          "silent failures | OOS declined | citation valid | figures supported | handed to person | tokens in/out |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    rows = []
    for c in summary["configs"]:
        tag = " (what the app ships)" if c == ship else " (THE baseline)" if c == base else ""
        rows.append((f"`{c}`{tag}", main_of(c)))
    if summary.get("no_retrieval_floor"):
        rows.append(("no retrieval (a floor, NOT the baseline)", summary["no_retrieval_floor"]))
    for name, a in rows:
        jf = f"{fmt(a.get('judge_faithful'))} (n={a.get('judge_n', 0)})" if a.get("judge_n") else "n/a"
        L.append(f"| {name} | {fmt(a['key_fact_pass'])} | {fmt(a['key_fact_pass_cross'])} | {jf} | "
                 f"{fmt(a.get('declined'))} | {fmt(a.get('declines_right'))} | "
                 f"{a.get('answered_without_evidence_n', 'n/a')} | {fmt(a['oos_correct'])} | "
                 f"{fmt(a.get('citation_valid'))} | {fmt(a.get('figures_supported'))} | {fmt(a.get('handoff'))} | "
                 f"{a['avg_tokens_in']:.0f} / {a['avg_tokens_out']:.0f} |")

    # ---- by question set ----------------------------------------------------------------------
    L += ["", "## By question set", "",
          "The main set was written before the system ran; the others were added later, so read them "
          "separately. The independent set was written by a different model from the documents alone.", "",
          "| set | system | scored questions | answer correctness | OOS declined | declined |",
          "|---|---|---|---|---|---|"]
    sets = [st for st in ("main", "extra", "breaker", "independent")
            if any(r["set"] == st for recs in results["configs"].values() for r in recs)]
    for st in sets:
        for c, recs in results["configs"].items():
            a = H.aggregate([r for r in recs if r["set"] == st])
            L.append(f"| {st} | `{c}` | {a['n_scored']} | {fmt(a['key_fact_pass'])} | "
                     f"{fmt(a['oos_correct'])} | {fmt(a.get('declined'))} |")
    L.append("")

    # ---- what failed, per config --------------------------------------------------------------
    evidence = {True: "needed docs retrieved", False: "needed docs NOT retrieved", None: "docs not recorded"}
    for c, recs in results["configs"].items():
        wrong = [r for r in recs if r["kind"] != "out_of_scope" and not r["key_fact_pass"]]
        L += [f"## `{c}`: scored questions that failed the correctness check ({len(wrong)})", ""]
        for r in wrong:
            L.append(f"- **{r['id']}** ({evidence[r.get('evidence_retrieved')]}): missing "
                     f"{r['missing_facts']}; answer: {r['answer'][:220]!r}")
        bad = [r for r in recs if r.get("judge_faithful") is False]
        L += ["", f"Judge marked {len(bad)} answers unfaithful:", ""]
        for r in bad:
            L.append(f"- **{r['id']}**: {r.get('judge_unsupported') or r.get('judge_why')}")
        L.append("")
    (out_dir / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def preflight(client, gen_model, judge_model, do_judge):
    """One tiny call to each model before the real run. A bad key, a wrong model id or an empty
    reply from a 'thinking' model shows up here for a fraction of a cent, not after 100 calls."""
    print("Preflight: one tiny call to each model...")
    targets = [("generation", gen_model)] + ([("judge", judge_model)] if do_judge else [])
    for label, model in targets:
        try:
            text, tok = H._generate(client, "Reply with the single word: ready", model=model, max_new_tokens=900)
        except Exception as e:  # noqa: BLE001
            sys.exit(f"\nPreflight FAILED for the {label} model `{model}`:\n  {e}\n"
                     "Nothing else was spent. Check the key, and that the model id exists on OpenRouter.")
        if not text.strip():
            sys.exit(f"\nPreflight: the {label} model `{model}` returned an empty reply even with a large "
                     "token budget. Try another model (--gen-model / --judge-model) or use --no-judge. "
                     "Nothing else was spent.")
        print(f"  {label} model `{model}` OK ({tok['in']} in / {tok['out']} out): {text[:30]!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--agreement", action="store_true")
    ap.add_argument("--configs", nargs="+", default=H.DEFAULT_RAG_CONFIGS, choices=list(H.CONFIGS))
    ap.add_argument("--gen-model", default=H.GEN_MODEL_DEFAULT)
    ap.add_argument("--judge-model", default=H.JUDGE_MODEL_DEFAULT)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--chunk-sweep", action="store_true", help="free: compare chunk sizes on retrieval recall")
    ap.add_argument("--leakage", action="store_true",
                    help="free: does a question already contain the answer? score before/after stripping")
    ap.add_argument("--abstain-below", type=float, default=None,
                    help="hand questions to a human (no model call) when the best retrieval score is below this")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--with-no-retrieval", action="store_true",
                    help="also run a model with NO retrieval, as a floor. Off by default: it is not the "
                         "baseline (it has never seen these documents), so it only confirms the obvious")
    args = ap.parse_args()

    if args.agreement:
        res = H.agreement()
        print("Nothing graded yet: set human_faithful to true/false in results/judge_spotcheck.json"
              if res is None else f"Agreement: {res[0]}/{res[1]}. Written to results/judge_agreement.md")
        return

    out_dir = H.RESULTS_DIR / "_dryrun" if args.dry_run else H.RESULTS_DIR
    questions = H.load_questions()
    if args.chunk_sweep:
        run_chunk_sweep(out_dir, questions)
        return
    if args.leakage:
        run_leakage(out_dir, questions)
        return
    print("Building index (loads the embedding model)...")
    idx = H.build_indexes()
    print("Embedder:", idx["plain"]["embedder"].using)

    per_config, report = write_retrieval_report(out_dir, questions, idx)
    print("\n" + report.split("\n## ")[0])
    if not (args.run or args.dry_run):
        print(f"\nWritten: {out_dir / 'retrieval_recall.md'}")
        return

    do_judge = not args.no_judge
    n_q = len(questions)
    n_scored = sum(1 for q in questions if q["kind"] != "out_of_scope")
    n_gen = n_q * (len(args.configs) + (1 if args.with_no_retrieval else 0))
    n_judge = n_scored * len(args.configs)
    words_sent = {c: d["all"]["avg_words"] for c, d in per_config.items()}
    est = cost_model.estimate_run(args.gen_model, args.judge_model, n_q, n_scored, args.configs, do_judge,
                                  words_sent=words_sent, no_retrieval_floor=args.with_no_retrieval)
    print(f"\nPlan: {n_gen} generation calls + up to {n_judge if do_judge else 0} judge calls "
          f"({len(args.configs)} configs, {n_q} questions"
          + (", plus the no-retrieval floor" if args.with_no_retrieval else "") + ").")
    print("Estimated upper-bound cost: " + (f"${est:.2f}" if est is not None else "unknown (model not in config.PRICES)"))
    if not (args.yes or args.dry_run):
        if input("Proceed and spend it? [y/N] ").strip().lower() != "y":
            print("Cancelled. Nothing spent.")
            return

    client = get_client(args.dry_run)
    preflight(client, args.gen_model, args.judge_model, do_judge)
    results = {"configs": {}}
    partial = {}

    def save_partial():
        (out_dir / "answers.partial.json").write_text(json.dumps(partial, indent=2), encoding="utf-8")

    def run_all(label, fn):
        out = []
        for n, q in enumerate(questions, 1):
            out.append(fn(q))
            if n % 8 == 0 or n == len(questions):
                print(f"  {label}: {n}/{len(questions)}")
        return out

    floor = None
    if args.with_no_retrieval:
        print("Running the no-retrieval floor (NOT the baseline; it has never seen these documents)...")
        floor = run_all("no-retrieval", lambda q: H.run_baseline_question(client, q, args.gen_model))
        partial["no_retrieval_floor"] = floor
        save_partial()
    for config in args.configs:
        print(f"Running {config}...")
        results["configs"][config] = run_all(
            config, lambda q: H.run_rag_question(client, q, config, idx, args.gen_model, args.judge_model, do_judge,
                                                 abstain_below=args.abstain_below))
        partial[config] = results["configs"][config]
        save_partial()

    summary = {"date": str(date.today()), "gen_model": args.gen_model,
               "judge_model": args.judge_model if do_judge else None,
               "embedder": idx["plain"]["embedder"].using,
               "shipped_config": H.SHIPPED, "baseline_config": H.BASELINE,
               "has_independent": any(q["set"] == "independent" for q in questions),
               "no_retrieval_floor": H.aggregate(floor) if floor else None,
               "configs": {c: H.aggregate(r) for c, r in results["configs"].items()},
               "retrieval": {c: d["main"] for c, d in per_config.items()}}
    summary["by_set"] = {"configs": {c: {st: H.aggregate([r for r in recs if r["set"] == st])
                                          for st in {r["set"] for r in recs}}
                                     for c, recs in results["configs"].items()}}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    answers = dict(results["configs"])
    if floor:
        answers["no_retrieval_floor"] = floor
    (out_dir / "answers.json").write_text(json.dumps(answers, indent=2), encoding="utf-8")
    write_eval_report(out_dir, summary, results)
    if do_judge:
        # Hand-check the judge on the system that ships, not on whichever config ran first.
        spot = H.SHIPPED if H.SHIPPED in results["configs"] else args.configs[0]
        items = H.make_spotcheck(results["configs"][spot], out_dir)
        print(f"\nWrote {len(items)} `{spot}` answers to {out_dir / 'judge_spotcheck.json'} for you to grade by hand,"
              " then run: python run_eval.py --agreement")
    print(f"\nDone. Read {out_dir / 'summary.md'}. Then: python cost_model.py")


if __name__ == "__main__":
    main()
