"""The failure found in the screen recordings, and the check that it stays fixed.

    python demo_citation_fix.py        live (needs a key; about $0.001)  -> results/citation_fix.md

What the recordings showed: Tanya replying "The documents do not say" to questions the retrieved
notes clearly answered, and citing the prompt's own placeholder text ("Cited: <doc_id>") or a
note's bracket NUMBER ("Cited: <1, 2>") instead of a real document id. Root causes: the grounded
prompt told the model to cite "the id" without saying which of the two things next to each note
was the id, and the impact brief gave the model no real id at all for the document it described.

This re-runs exactly the two situations from the recordings:
  1. CD1 in chat: "What packaging change forced F&B to order new CNC tooling, and what was
     delivered?" -- recorded abstaining although the top note answered it.
  2. The Meadowfield upload -> impact brief -> "Which business domains does Meadowfield Snacks
     affect?" -- recorded citing "<doc_id>", then abstaining with a fake "Cited: <1, 2>".

The upload is built in memory exactly as the app files it (rag_core.format_upload_content, the
same upload-<division>-<stem> ids), on top of the FIXED corpus only, so leftover files in
data/uploads/ from using the app cannot add duplicate hits and move the result.

What counts as the bug (guardrails.malformed_citation): a FAKE citation -- a bracket number or
placeholder standing in for a real id. An honest "The documents do not say" with no citation, or
with a real id it looked at, is a defensible "not sure", not this bug, and passes; the separate,
remaining over-caution it can show is reported in docs/TRADEOFF_ANALYSIS.md.
"""
import sys
from datetime import date

import config
import doc_parser
import guardrails
import rag_core
import run_eval  # for load_key: the same key convention as the live evaluation


def check_citation(label, answer, docs_by_id, should_abstain=False):
    abstained = guardrails.is_abstention(answer)
    cited = guardrails.cited_doc_ids(answer, docs_by_id)
    malformed = guardrails.malformed_citation(answer, docs_by_id)
    verdict = []
    if should_abstain:
        verdict.append(("abstained as expected", abstained))
        verdict.append(("no fake/malformed citation while abstaining", not malformed))
    elif abstained:
        # Expected an answer, got an honest decline: not the recorded bug, as long as it is not
        # dressed up with a fake citation.
        verdict.append(("no fake/malformed citation while abstaining", not malformed))
    else:
        verdict.append(("cited at least one REAL document id", bool(cited)))
        unsupported = guardrails.unsupported_figures(answer, docs_by_id)
        verdict.append(("no unsupported figures", not unsupported))
    ok = all(v for _, v in verdict)
    print(f"\n=== {label} ===\n{answer}")
    for desc, v in verdict:
        print(f"  [{'PASS' if v else 'FAIL'}] {desc}")
    return {"label": label, "answer": answer, "abstained": abstained, "cited": sorted(cited),
            "checks": verdict, "pass": ok}


def main():
    key, source = run_eval.load_key()
    if not key:
        import getpass
        key = getpass.getpass("Paste your OpenRouter API key (hidden): ").strip()
    else:
        print(f"Using the OpenRouter key from {source}.")
    from openai import OpenAI
    client = OpenAI(base_url=config.BASE_URL, api_key=key)

    print("Preflight...")
    text, _ = rag_core.generate(client, "Reply with the word: ready", model=config.GEN_MODEL, max_new_tokens=900)
    if not text.strip():
        sys.exit("Preflight got an empty reply -- stopping before the real test. Nothing else was spent.")

    fixed = [d for d in rag_core.load_corpus() if d["source"] == "fixed"]
    results = []

    # ---- 1. CD1, no upload involved --------------------------------------------------------------
    docs, chunks, matrix, embedder = rag_core.build_index(fixed)
    docs_by_id = {d["doc_id"]: d["text"] for d in docs}
    q = "What packaging change forced F&B to order new CNC tooling, and what was delivered?"
    answer, _, _ = rag_core.answer_question(client, q, chunks, matrix, embedder)
    results.append(check_citation("1. CD1 in chat (no upload)", answer, docs_by_id))

    # ---- 2. the Meadowfield upload, filed under fnb and cnc as in the recording -------------------
    sample = config.DATA_DIR / "sample_uploads" / "meadowfield_snacks_onboarding.docx"
    raw = doc_parser.extract_text(sample.name, sample.read_bytes())
    divisions, stem = ["fnb", "cnc"], "meadowfield_snacks_onboarding"
    saved = rag_core.format_upload_content(raw, divisions)
    upload_docs = [{"doc_id": f"upload-{d}-{stem}", "division": d, "path": f"data/uploads/{d}/{stem}.md",
                    "text": saved, "source": "upload"} for d in divisions]
    docs, chunks, matrix, embedder = rag_core.build_index(fixed + upload_docs)
    docs_by_id = {d["doc_id"]: d["text"] for d in docs}

    brief, _, _ = rag_core.generate_impact_snapshot(
        client, saved, divisions, [d["doc_id"] for d in upload_docs], chunks, matrix, embedder)
    results.append(check_citation("2a. Upload impact brief", brief, docs_by_id))
    followup = "Which business domains does Meadowfield Snacks affect?"
    answer, _, _ = rag_core.answer_question(client, followup, chunks, matrix, embedder)
    results.append(check_citation("2b. Follow-up chat question", answer, docs_by_id))

    n_ok = sum(r["pass"] for r in results)
    L = ["# The recorded citation bug, re-run", "",
         f"`python demo_citation_fix.py`, {date.today()}, generation `{config.GEN_MODEL}`. "
         "The bug: an answer or an abstention dressed up with a FAKE citation (the prompt's placeholder, "
         "or a note's bracket number) instead of a real document id. See the module docstring for the "
         "root causes and the fix.", "",
         f"**{n_ok}/{len(results)} cases pass.**", ""]
    for r in results:
        L += [f"## {r['label']}: {'PASS' if r['pass'] else 'FAIL'}", "", "```", r["answer"], "```", ""]
        L += [f"- [{'x' if v else ' '}] {d}" for d, v in r["checks"]] + [""]
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / "citation_fix.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\n{n_ok}/{len(results)} cases passed. Written: results/citation_fix.md")
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
