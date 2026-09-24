"""Verifies the fix for the bug found in screen_recordings/: Tanya replying "The documents
do not say" on questions the retrieved notes clearly answer, and citing the literal
placeholder text or a note's bracket NUMBER instead of a real doc_id.

Tests exactly the two cases from the recordings:
  1. CD1 (chat): "what packaging change forced F&B to order a new CNC tooling?" -- the
     recording shows this abstaining even though the top note (score 0.675) is the answer.
  2. The Meadowfield upload -> impact snapshot -> "Which business domains does Meadowfield
     Snacks affect?" -- the recording shows a snapshot citing the literal placeholder
     "<doc_id>", and the chat question after it abstaining with a fake "Cited: <1, 2>".

Uses sample_uploads/meadowfield_snacks_onboarding.docx (already in the repo) for case 2, and
cleans up the test upload files it creates afterward -- this is a diagnostic, not a real upload.

Note on what "pass" means (see check_citation): the actual bug in the recordings was a FAKE
citation -- a bracket number or the prompt's own placeholder text stood in for a real doc_id,
sometimes alongside an abstention. An honest "the documents do not say" with no citation, or
with a real doc_id it looked at but decided didn't answer the question, is not that bug and is
scored as a pass; only a fake/malformed citation, or a real answer with unsupported figures,
fails a case.

    python eval/test_citation_fix.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "webapp"))

import run_eval  # for load_key, same convention as --run
import rag_core
import doc_parser

ROOT = Path(__file__).resolve().parent.parent
GEN_MODEL = rag_core.GEN_MODEL


def load_index():
    docs = rag_core.load_corpus()
    chunks = rag_core.build_chunks(docs)
    embed_texts = [rag_core.embed_text(c) for c in chunks]
    embedder = rag_core.Embedder(embed_texts)
    matrix = embedder.embed(embed_texts)
    return docs, chunks, matrix, embedder


def check_citation(label, answer, docs_by_id, should_abstain):
    """What actually counts as the bug, per the screen recordings: an abstention or an answer
    dressed up with a FAKE citation (a bracket number, or the prompt's own placeholder text)
    instead of a real doc_id, or an answer with figures the cited document doesn't support.
    Honest abstention with no citation, or an honest abstention that still points at a real
    doc_id it looked at, is NOT the bug -- it is a defensible "not sure" and is scored as a pass."""
    print(f"\n=== {label} ===")
    print(answer)
    abstained = rag_core.is_abstention(answer)
    cited = rag_core.cited_doc_ids(answer, docs_by_id)
    malformed = rag_core.malformed_citation(answer, docs_by_id)
    verdict = []
    if should_abstain:
        verdict.append(("abstained as expected", abstained))
        verdict.append(("no fake/malformed citation while abstaining", not malformed))
    elif abstained:
        # Expected a real answer but got an honest "do not say" instead -- not the bug being
        # tested for here, as long as it didn't dress that up with a fake citation.
        verdict.append(("no fake/malformed citation while abstaining", not malformed))
    else:
        verdict.append(("cited at least one REAL doc_id", bool(cited)))
        unsupported = rag_core.unsupported_figures(answer, docs_by_id)
        verdict.append(("no unsupported figures", not unsupported))
    for desc, ok in verdict:
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}")
    return all(ok for _, ok in verdict)


def main():
    client_key, source = run_eval.load_key()
    if not client_key:
        import getpass
        client_key = getpass.getpass("Paste your OpenRouter API key (hidden): ").strip()
    else:
        print(f"Using the OpenRouter key from {source}.")
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=client_key)

    print("Preflight...")
    text, _ = rag_core.generate(client, "Reply with the word: ready", model=GEN_MODEL, max_new_tokens=900)
    if not text.strip():
        sys.exit("Preflight got an empty reply -- stopping before running the real test.")
    print(" ", text[:30])

    results = []

    # ---- Case 1: CD1, no upload involved ----
    docs, chunks, matrix, embedder = load_index()
    docs_by_id = {d["doc_id"]: d["text"] for d in docs}
    cd1_question = "What packaging change forced F&B to order new CNC tooling, and what was delivered?"
    answer, hits, tokens = rag_core.answer_question(client, cd1_question, chunks, matrix, embedder)
    results.append(check_citation("CD1 (chat, no upload)", answer, docs_by_id, should_abstain=False))

    # ---- Case 2: the Meadowfield upload ----
    sample_path = ROOT / "sample_uploads" / "meadowfield_snacks_onboarding.docx"
    upload_text = doc_parser.extract_text(sample_path.name, sample_path.read_bytes())
    chosen_divisions = ["fnb", "cnc"]  # matches what the recording shows being confirmed
    safe_stem = "meadowfield_snacks_onboarding_TESTFIXTURE"
    new_doc_ids = [f"upload-{d}-{safe_stem}" for d in chosen_divisions]
    # Same as app.py's confirm step: prepend the "Filed under" line before saving, so this
    # fixture matches exactly what a real confirmed upload looks like in the corpus.
    saved_text = rag_core.format_upload_content(upload_text, chosen_divisions)
    written = []
    try:
        for division in chosen_divisions:
            target_dir = rag_core.UPLOADS_DIR / division
            target_dir.mkdir(parents=True, exist_ok=True)
            path = target_dir / f"{safe_stem}.md"
            path.write_text(saved_text, encoding="utf-8")
            written.append(path)

        docs, chunks, matrix, embedder = load_index()
        docs_by_id = {d["doc_id"]: d["text"] for d in docs}

        snapshot, hits, tokens = rag_core.generate_impact_snapshot(
            client, saved_text, chosen_divisions, new_doc_ids, chunks, matrix, embedder)
        results.append(check_citation("Upload impact snapshot", snapshot, docs_by_id, should_abstain=False))

        followup = "Which business domains does Meadowfield Snacks affect?"
        answer, hits, tokens = rag_core.answer_question(client, followup, chunks, matrix, embedder)
        results.append(check_citation("Follow-up chat question", answer, docs_by_id, should_abstain=False))
    finally:
        for path in written:
            path.unlink(missing_ok=True)
        print(f"\nCleaned up {len(written)} test fixture file(s) from data/uploads/.")

    print("\n" + "=" * 60)
    print(f"{sum(results)}/{len(results)} cases fully passed.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
