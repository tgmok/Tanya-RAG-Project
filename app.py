"""Tanya -- Streamlit demo UI.

Run from the repository root:
    streamlit run app.py

It reads the fixed evaluation corpus (data/fnb, data/cnc, data/jewellery) read-only and writes
uploaded documents only to data/uploads/<division>/, which git and the evaluation both ignore,
so nothing done in the app can move a reported number. See docs/SYSTEM_FLOW.md for the data flow.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import config
import doc_parser
import guardrails
import rag_core

st.set_page_config(page_title="Tanya · TGMOK Holdings", page_icon="\U0001F4C4", layout="wide")


# ---------------------------------------------------------------------------
# Session state / index building
# ---------------------------------------------------------------------------

def init_state():
    defaults = {
        "client": None,
        "docs": None,
        "chunks": None,
        "matrix": None,
        "embedder": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "chat_history": [],
        "pending_upload": None,  # holds classification result awaiting confirmation
        "uploader_key": 0,  # bumped to force-clear the file_uploader widget -- see the comment
                            # at its call site for why this is needed, not cosmetic
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def rebuild_index():
    docs, chunks, matrix, embedder = rag_core.build_index()
    st.session_state.docs = docs
    st.session_state.chunks = chunks
    st.session_state.matrix = matrix
    st.session_state.embedder = embedder


def add_tokens(tokens):
    st.session_state.tokens_in += tokens.get("in", 0)
    st.session_state.tokens_out += tokens.get("out", 0)


def budget_ok():
    """Guardrail: stop loudly and refuse further model calls once the session cap is hit,
    rather than spending without limit. Returns False (and shows the stop) if over budget."""
    if guardrails.session_tokens_exceeded(st.session_state.tokens_in, st.session_state.tokens_out):
        st.error(
            f"Session token cap reached ({st.session_state.tokens_in + st.session_state.tokens_out:,} "
            f"/ {config.MAX_SESSION_TOKENS:,} tokens). No further model calls this session -- "
            "reload the page to reset. This is a guardrail against unbounded spend (OWASP LLM10), "
            "not a cost estimate; at gpt-4o-mini prices the cap itself costs under $0.05."
        )
        return False
    return True


init_state()
if st.session_state.docs is None:
    with st.spinner("Loading TGMOK Holdings' document corpus..."):
        rebuild_index()


# ---------------------------------------------------------------------------
# Sidebar -- key entry (session-only, never written to disk) and corpus status
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Connection")
    api_key = st.text_input(
        "OpenRouter API key", type="password",
        help="Kept only in this browser session's memory. Never written to disk, "
             "never logged. Cleared when you close this tab.",
    )
    if api_key and st.session_state.client is None:
        from openai import OpenAI
        st.session_state.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        st.success("Connected.")
    elif not api_key:
        st.session_state.client = None
        st.info("Paste your OpenRouter key to enable generation. Retrieval still "
                "works without one -- you'll see which chunks match, just not a "
                "generated answer.")

    st.divider()
    st.header("Corpus status")
    fixed_count = sum(1 for d in st.session_state.docs if d["source"] == "fixed")
    upload_count = sum(1 for d in st.session_state.docs if d["source"] == "upload")
    st.metric("Fixed (graded) documents", fixed_count)
    st.metric("Uploaded documents", upload_count)
    st.caption(st.session_state.embedder.using)
    st.caption(f"Tokens this session: {st.session_state.tokens_in} in / "
               f"{st.session_state.tokens_out} out (cap {config.MAX_SESSION_TOKENS:,})")
    if st.button("Rebuild index"):
        rebuild_index()
        st.rerun()
    abstain_below = st.slider(
        "Abstain below retrieval score", 0.0, 0.8, float(config.ABSTAIN_BELOW), 0.01,
        help="If the best-matching note scores below this, Tanya does not answer and passes the question to "
             "a human. Retrieval score is a weak signal here (see results/retrieval_recall.md), so this is a "
             "backstop, not a guarantee.")

    st.divider()
    st.caption(
        "Uploads go to `data/uploads/`, separate from the fixed, hand-verified corpus the "
        "evaluation uses, so nothing done here can move a reported number."
    )


st.title("Tanya")
st.caption("TGMOK Holdings' cross-division assistant — F&B · CNC · Jewellery")


# ---------------------------------------------------------------------------
# Upload section
# ---------------------------------------------------------------------------

st.subheader("1 · Upload a document (optional)")
st.caption(
    "Upload a new document (PDF, DOCX, or plain text). Tanya will classify which "
    "division(s) it affects and generate a snapshot of how it connects to the "
    "other divisions' existing records. You can also skip this and just ask a "
    "question below."
)

uploaded_file = st.file_uploader(
    "Choose a file", type=["pdf", "docx", "txt", "md"],
    key=f"file_uploader_{st.session_state.uploader_key}",
    # Streamlit keeps a file_uploader's file across reruns until the widget's key changes --
    # it does NOT clear on its own after we act on the file. Without this, "Cancel upload"
    # would re-trigger classification on the very next rerun (st.rerun() itself), and a
    # confirmed upload would silently reclassify itself again on the next unrelated
    # interaction (e.g. asking a chat question). Bumping uploader_key below forces a fresh,
    # empty widget once we're done with a file.
)

if uploaded_file is not None and st.session_state.pending_upload is None:
    try:
        text = doc_parser.extract_text(uploaded_file.name, uploaded_file.getvalue())
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read this file: {e}")
        text = None

    if text:
        if not text.strip():
            st.warning("No extractable text found in this file (it may be a scanned "
                       "image PDF with no text layer).")
        else:
            flags = guardrails.scan_for_injection(text)
            if flags:
                st.warning(
                    "This document contains a phrase commonly seen in prompt-injection attempts, "
                    "so it was NOT sent to the classifier automatically: "
                    + ", ".join(f"'{f}'" for f in flags)
                    + ". Read the document yourself and pick its division(s) below if it is legitimate."
                )
                st.session_state.pending_upload = {
                    "filename": uploaded_file.name, "text": text,
                    "classification": {"error": "Skipped automatic classification (see warning above).",
                                       "flagged_phrases": flags},
                }
                st.rerun()
            elif st.session_state.client is None:
                st.warning("Paste your OpenRouter API key in the sidebar to classify "
                           "and analyse this document.")
            elif not budget_ok():
                pass
            else:
                with st.spinner("Classifying which division(s) this document affects..."):
                    result = rag_core.classify_document(st.session_state.client, text)
                if "tokens" in result:
                    add_tokens(result["tokens"])
                st.session_state.pending_upload = {
                    "filename": uploaded_file.name,
                    "text": text,
                    "classification": result,
                }
                st.rerun()

if st.session_state.pending_upload is not None:
    pu = st.session_state.pending_upload
    classification = pu["classification"]

    st.markdown(f"**File:** `{pu['filename']}`")
    if "error" in classification:
        st.warning(classification["error"])
        suggested = []
    else:
        st.markdown(f"**Tanya's read:** {classification['summary']}")
        st.caption(f"Reasoning: {classification['reasoning']}")
        suggested = classification["divisions"]

    st.markdown("**Confirm which division(s) this belongs to** (edit if Tanya got it wrong):")
    cols = st.columns(3)
    chosen = []
    for i, division in enumerate(config.DIVISIONS):
        with cols[i]:
            if st.checkbox(division, value=(division in suggested), key=f"div_{division}"):
                chosen.append(division)

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        confirm = st.button("Confirm and file document", type="primary", disabled=not chosen)
    with col_cancel:
        cancel = st.button("Cancel upload")

    if cancel:
        st.session_state.pending_upload = None
        st.session_state.uploader_key += 1  # clear the file so cancelling actually cancels
        st.rerun()

    if confirm and chosen and not budget_ok():
        pass
    elif confirm and chosen:
        safe_stem = Path(pu["filename"]).stem.replace(" ", "_")
        new_doc_ids = [f"upload-{division}-{safe_stem}" for division in chosen]
        saved_text = rag_core.format_upload_content(pu["text"], chosen)
        for division in chosen:
            target_dir = config.UPLOADS_DIR / division
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / f"{safe_stem}.md").write_text(saved_text, encoding="utf-8")

        with st.spinner("Rebuilding the retrieval index with the new document..."):
            rebuild_index()

        with st.spinner("Generating cross-division impact snapshot..."):
            snapshot, hits, tokens = rag_core.generate_impact_snapshot(
                st.session_state.client, saved_text, chosen, new_doc_ids,
                st.session_state.chunks, st.session_state.matrix, st.session_state.embedder,
            )
            add_tokens(tokens)

        st.success(f"Filed under: {', '.join(chosen)}")
        st.markdown("### Cross-division impact snapshot")
        st.info(snapshot)
        docs_by_id = {d["doc_id"]: d["text"] for d in st.session_state.docs}
        unsupported = guardrails.unsupported_figures(snapshot, docs_by_id)
        if unsupported:
            st.warning("Not found in the cited documents: " + ", ".join(unsupported)
                       + ". Check these against the source before relying on this snapshot.")
        elif unsupported is None and not guardrails.is_abstention(snapshot):
            st.warning("This snapshot cites no existing document, so its figures could not be checked "
                       "against the corpus (it may only be describing the new upload itself).")
        with st.expander("Notes this snapshot drew on"):
            for h in hits:
                st.markdown(f"- **{h['doc_id']}** · {h.get('title', '')} ({h['division']}, score {h['score']:.3f}): "
                            f"{h['text'][:200]}...")
        st.caption(
            "This snapshot is a demo aid for a human to read and judge -- it is not "
            "added to data/eval_questions.json as a scored case, since there is no "
            "pre-verified ground truth for a document uploaded live."
        )
        st.session_state.pending_upload = None
        st.session_state.uploader_key += 1  # clear the file so it isn't reclassified on the
                                            # next unrelated interaction (e.g. a chat question)


st.divider()

# ---------------------------------------------------------------------------
# Chat section -- works with or without an upload above
# ---------------------------------------------------------------------------

st.subheader("2 · Ask Tanya a question")

for turn in st.session_state.chat_history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        if turn["role"] == "assistant" and turn.get("hits"):
            with st.expander("Retrieved notes"):
                for h in turn["hits"]:
                    st.markdown(f"- **{h['doc_id']}** · {h.get('title', '')} ({h['division']}, score "
                                f"{h['score']:.3f}): {h['text'][:200]}...")

question = st.chat_input("Ask about any division, or a cross-division question...")
if question:
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if st.session_state.client is None:
            hits = rag_core.retrieve(
                question, st.session_state.chunks, st.session_state.matrix,
                st.session_state.embedder,
            )
            answer = ("*(No API key set -- showing retrieved notes only, no "
                      "generated answer.)*")
            st.markdown(answer)
            with st.expander("Retrieved notes"):
                for h in hits:
                    st.markdown(f"- **{h['doc_id']}** · {h.get('title', '')} ({h['division']}, score "
                                f"{h['score']:.3f}): {h['text'][:200]}...")
        elif not budget_ok():
            answer, hits = None, []
        else:
            with st.spinner("Retrieving and answering..."):
                answer, hits, tokens = rag_core.answer_question(
                    st.session_state.client, question,
                    st.session_state.chunks, st.session_state.matrix, st.session_state.embedder,
                    abstain_below=abstain_below,
                )
                add_tokens(tokens)
            st.markdown(answer)
            docs_by_id = {d["doc_id"]: d["text"] for d in st.session_state.docs}
            unsupported = guardrails.unsupported_figures(answer, docs_by_id)
            if unsupported:
                st.warning("Not found in the cited documents: " + ", ".join(unsupported)
                           + ". Check these against the source before relying on this answer.")
            elif unsupported is None and not guardrails.is_abstention(answer):
                st.warning("This answer cites no document, so its figures could not be checked.")
            with st.expander("Retrieved notes"):
                for h in hits:
                    st.markdown(f"- **{h['doc_id']}** · {h.get('title', '')} ({h['division']}, score "
                                f"{h['score']:.3f}): {h['text'][:200]}...")

        if answer is not None:
            st.session_state.chat_history.append({
                "role": "assistant", "content": answer, "hits": hits,
            })
