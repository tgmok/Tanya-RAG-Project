"""Shared retrieval/generation logic for Tanya's Streamlit demo.

This module is ADDITIVE to the project: it only READS from data/fnb, data/cnc,
data/jewellery (the fixed, hand-verified evaluation corpus) and WRITES only to
data/uploads/<division>/ (a separate folder, kept apart from the graded corpus on
purpose -- see docs/SYSTEM_FLOW.md). Nothing here modifies eval_questions.json,
data_dictionary.json, or check_my_data.py.

Mirrors the retrieval/grounding design already built and tested in
Tanya_RAG_Notebook.ipynb, plus a document classification step whose JSON-robustness
follows the lessons documented in the 203 project's llm-resume-parse-incident.md:
request JSON only with an explicit schema, use a generous token budget (reasoning
models can silently truncate), extract JSON defensively with regex rather than
trusting the whole response is clean JSON, and normalize near-miss shapes instead of
failing outright.
"""
import json
import os
import re
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DIVISIONS = ["fnb", "cnc", "jewellery"]

CHUNK_WORDS = 200  # measured offline (results/chunk_sweep.md): cross-division recall 82% -> 91%,
OVERLAP = 50        # doc recall 84% -> 92% vs 60/15, at ~3x the words sent per query (286 -> 821)
TOP_K = 5   # measured offline: cross-division recall 73% -> 82%, document recall 71% -> 81% vs top-3

# Backstop, not a guarantee: the best retrieval score separates answerable questions from
# absent-but-plausible ones only weakly (see results/retrieval_recall.md, abstention table).
ABSTAIN_BELOW = 0.45

# Guardrail, not a cost estimate: stops the session loudly rather than spending without limit
# (problem statement Section 8; OWASP LLM10:2025 Unbounded Consumption). At gpt-4o-mini prices
# this is under $0.05 even fully spent -- the point is a hard, visible stop, not the number.
MAX_SESSION_TOKENS = 100_000


def session_tokens_exceeded(tokens_in, tokens_out, cap=MAX_SESSION_TOKENS):
    return (tokens_in + tokens_out) >= cap


# Uploaded documents are untrusted input (OWASP LLM01:2025 Prompt Injection): the classifier
# below reads the raw upload text with an LLM call, so a phrase aimed at that model rather than
# at the reader is a real risk. This is a code-side SCAN, not a filter -- it never edits the
# text or blocks the upload; it routes the document to manual division selection instead of
# the automatic classifier call, and shows the user exactly what matched. False positives are
# expected (a real SOP can legitimately contain the word "instructions"); that is the accepted
# cost of a cheap, auditable check.
INJECTION_PATTERNS = [
    r"ignore (?:the )?(?:previous|prior|above|all) instructions",
    r"disregard (?:the )?(?:previous|prior|above) instructions",
    r"new instructions\s*:",
    r"system prompt",
    r"you are now",
    r"act as (?:a |an )?(?!auditor\b)",   # "act as an auditor" is fine, other roleplay is flagged
    r"reveal (?:your|the) (?:prompt|instructions|system message)",
    r"\bDAN\b",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def scan_for_injection(text):
    """Return the distinct matched phrases (as they appear in the text), or [] if none."""
    return list(dict.fromkeys(m.group(0) for m in _INJECTION_RE.finditer(text or "")))

GEN_MODEL = "openai/gpt-4o-mini"  # what the A1 starters used. gpt-5-mini (named in the problem
                                  # statement) returned an empty reply in this setup, cause not isolated.

GROUNDED = (
    "Answer using ONLY the numbered notes provided below. Each note reads "
    "\"[N] (doc_id) text\" -- the id you must cite is whatever text appears in the "
    "parentheses right after the bracket number, copied exactly, not shortened or "
    "reformatted. It is NEVER the bracket number N itself; N is only a position marker "
    "for your own reading, not an id. If the notes answer the question, even partially, "
    "use them and answer with what they support. Only if the notes truly contain nothing "
    "relevant, reply exactly: The documents do not say. Do not use any other knowledge. "
    "Finish every reply with exactly one line: 'Cited: ' followed by the real id(s) you "
    "used, comma-separated. This is a FORMAT example only, with ids that do not exist in "
    "this corpus -- never reuse them, always substitute the real id(s) from the notes "
    "above: Cited: abc-01, xyz-02"
)

CLASSIFY_SYSTEM = (
    "You are a document router for TGMOK Holdings, a conglomerate with three "
    "divisions: fnb (F&B contract manufacturing), cnc (CNC precision machine parts), "
    "and jewellery (gold jewellery manufacturing & retail).\n"
    "Read the document text and decide which division(s) it affects. A document can "
    "affect more than one division (e.g. a packaging change that also requires new "
    "tooling touches both fnb and cnc).\n\n"
    "Reply with ONLY a JSON object, no prose, no markdown code fence, in exactly "
    "this shape:\n"
    '{"divisions": ["fnb", "cnc"], "reasoning": "one sentence explaining why", '
    '"summary": "one or two sentence summary of what the document is about"}\n'
    'divisions must be a list containing only values from: "fnb", "cnc", "jewellery".'
)


# ---------------------------------------------------------------------------
# Corpus loading (fixed corpus + uploads), chunking, embedding, retrieval
# ---------------------------------------------------------------------------

def format_upload_content(text, divisions):
    """Prepend an explicit division-filing line before saving an upload.

    Every FIXED corpus document states its own division in a header line (e.g.
    "**Division:** F&B Contract Manufacturing (TGMOK Holdings)") -- that fact is literal
    text the grounded prompt can point to. An uploaded document had no such line: it was
    saved byte-for-byte as extracted, so which division(s) it was filed under existed only
    as the classifier's separate output, never as text in the corpus itself. Observed
    effect: asked "which divisions does this affect?", the model correctly (by its own
    literal-grounding rule) said the documents do not say -- the fact was true but never
    actually stated in what it was allowed to read. This line makes it stated, consistent
    with how every other document in the corpus already works."""
    return f"**Filed under:** {', '.join(divisions)} (uploaded document)\n\n{text}"


def load_corpus():
    """Load every .md document from data/<division>/ and data/uploads/<division>/.

    Returns a list of dicts: {doc_id, division, path, text, source}.
    source is 'fixed' for the graded corpus, 'upload' for anything a user added
    through this app -- kept distinct so the UI can always show which is which.

    An uploaded document filed under multiple divisions is saved once per division
    (see app.py's confirm step) with IDENTICAL text; its doc_id includes the division
    so each copy is unique. Without this, two divisions' copies of the same file would
    collide on one doc_id, and anything keyed by doc_id (docs_by_id in app.py, the
    citation-content check) would silently drop one of them.
    """
    docs = []
    for division in DIVISIONS:
        fixed_dir = DATA_DIR / division
        if fixed_dir.exists():
            for f in sorted(fixed_dir.glob("*.md")):
                docs.append({
                    "doc_id": f.stem,
                    "division": division,
                    "path": str(f.relative_to(PROJECT_ROOT)),
                    "text": f.read_text(encoding="utf-8"),
                    "source": "fixed",
                })
        upload_dir = UPLOADS_DIR / division
        if upload_dir.exists():
            for f in sorted(upload_dir.glob("*.md")):
                docs.append({
                    "doc_id": f"upload-{division}-{f.stem}",
                    "division": division,
                    "path": str(f.relative_to(PROJECT_ROOT)),
                    "text": f.read_text(encoding="utf-8"),
                    "source": "upload",
                })
    return docs


def chunk(text, size=CHUNK_WORDS, overlap=OVERLAP):
    words, out, i = text.split(), [], 0
    while i < len(words):
        out.append(" ".join(words[i:i + size]))
        if i + size >= len(words):
            break
        i += max(1, size - overlap)
    return out


def build_chunks(docs):
    chunks = []
    for d in docs:
        # Fixed corpus docs all start with a "# Title" line (hand-authored convention); an
        # upload usually won't, so this falls back to the doc_id rather than raising -- same
        # fallback eval/harness.py uses. See embed_text() for why the title matters at all.
        title = next((ln[2:].strip() for ln in d["text"].splitlines() if ln.startswith("# ")), d["doc_id"])
        for c in chunk(d["text"]):
            chunks.append({"text": c, "doc_id": d["doc_id"], "division": d["division"], "title": title})
    return chunks


def embed_text(c):
    """The string actually embedded for retrieval matching -- the chunk's own document title
    prepended to its text. Measured in results/chunk_sweep.md / retrieval_recall.md: at the
    200-word chunking adopted in round 7, this ('titled_k5') reaches 100% cross-division /
    100% doc recall, against 91%/88% for plain chunk text. The text shown to the model and
    checked for citations (h['text'], the doc content itself) is UNCHANGED by this -- titling
    only changes what similarity is computed against, not what the model reads or what
    unsupported_figures() verifies against, so it costs nothing extra in generation tokens."""
    return f"{c['title']}. {c['text']}"


class Embedder:
    """Local sentence-transformers embeddings, TF-IDF fallback -- same pattern as
    the notebook. Built once per Streamlit session and cached in session_state."""

    def __init__(self, chunk_texts):
        self.using = None
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self.using = "local embeddings (all-MiniLM-L6-v2) -- matches MEANING"
        except Exception as e:  # noqa: BLE001 -- intentionally broad, see notebook
            self._model = None
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer().fit(chunk_texts)
            self.using = f"TF-IDF fallback -- matches WORDS, not meaning ({str(e)[:80]})"

    def embed(self, texts):
        texts = list(texts)
        if self._model is not None:
            return np.asarray(self._model.encode(texts, normalize_embeddings=True))
        m = self._vectorizer.transform(texts).toarray()
        n = np.linalg.norm(m, axis=1, keepdims=True)
        return m / np.where(n == 0, 1, n)


def retrieve(question, chunks, matrix, embedder, k=TOP_K, divisions=None):
    q = embedder.embed([question])[0]
    scores = matrix @ q
    if divisions is not None:
        mask = np.array([0.0 if c["division"] in divisions else -np.inf for c in chunks])
        scores = scores + mask
    order = np.argsort(-scores)[:k]
    return [
        {**chunks[i], "score": float(scores[i])}
        for i in order
    ]


# ---------------------------------------------------------------------------
# Generation (OpenRouter). Client is passed in from the Streamlit app, which
# owns the key -- this module never reads or stores it itself.
# ---------------------------------------------------------------------------

def generate(client, prompt, system=None, model=None, max_new_tokens=500, temperature=0.0):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    r = client.chat.completions.create(
        model=model or GEN_MODEL, messages=msgs,
        temperature=temperature, max_tokens=max_new_tokens,
    )
    content = r.choices[0].message.content
    usage = getattr(r, "usage", None)
    tokens = {
        "in": usage.prompt_tokens if usage else 0,
        "out": usage.completion_tokens if usage else 0,
    }
    return (content or "").strip(), tokens


def is_abstention(answer):
    return "do not say" in (answer or "").lower()


def handoff_message(top_score, threshold):
    return (f"The documents do not say. [Low retrieval confidence: the best match scored {top_score:.2f}, below "
            f"{threshold:.2f}, so this question is passed to a human reviewer instead of being answered.]")


def cited_doc_ids(answer, known_ids):
    m = re.search(r"cited:\s*(.+)$", answer or "", re.I | re.S)
    if not m:
        return set()
    tail = m.group(1).lower()
    return {d for d in known_ids if d.lower() in tail}


def malformed_citation(answer, known_ids):
    """True only for the specific bug seen in the screen recordings: a 'Cited:' line that
    has SOMETHING in it, but nothing that resolves to a real known id -- e.g. a leftover
    bracket number ("Cited: <1, 4>") or the prompt's own placeholder text ("Cited: <doc_id>").
    A missing or empty 'Cited:' line is NOT malformed -- that is just an honest answer or
    abstention that offers no citation, which is fine on its own."""
    m = re.search(r"cited:\s*(.+)$", answer or "", re.I | re.S)
    if not m:
        return False
    tail = m.group(1).strip()
    if not tail:
        return False
    return not cited_doc_ids(answer, known_ids)


_FIGURE = re.compile(r"\d{4}-\d{2}-\d{2}|[A-Z]{1,5}(?:-[A-Z0-9]+)+|\$?\d[\d,]*\.?\d*%?")


def unsupported_figures(answer, docs_by_id):
    """Code check that a cited document really contains the figures in the answer (the Section 8
    citation-verification mitigation). Returns the numbers, dates and ids in the answer that appear
    in NONE of the cited documents; [] if all are supported; None if the answer abstains or cites
    no known document (nothing to verify against)."""
    if is_abstention(answer):
        return None
    cited = cited_doc_ids(answer, docs_by_id)
    if not cited:
        return None
    body = re.split(r"cited:", answer, flags=re.I)[0]
    source = " ".join(docs_by_id[d] for d in cited).lower().replace(",", "")
    bad = []
    for tok in _FIGURE.findall(body):
        t = tok.lower().replace(",", "").lstrip("$").rstrip(".")
        if "%" not in t and len(re.sub(r"\D", "", t)) < 2:
            continue                      # list numbers such as "1." or "2"
        if t not in source and tok not in bad:
            bad.append(tok)
    return bad


def answer_question(client, question, chunks, matrix, embedder, k=TOP_K, divisions=None,
                    abstain_below=ABSTAIN_BELOW):
    hits = retrieve(question, chunks, matrix, embedder, k=k, divisions=divisions)
    if abstain_below is not None and hits and hits[0]["score"] < abstain_below:
        return handoff_message(hits[0]["score"], abstain_below), hits, {"in": 0, "out": 0}
    context = "\n\n".join(f"[{i+1}] ({h['doc_id']}) {h['text']}" for i, h in enumerate(hits))
    answer, tokens = generate(client, f"NOTES:\n{context}\n\nQUESTION: {question}", system=GROUNDED)
    return answer, hits, tokens


# ---------------------------------------------------------------------------
# Document classification -- the 203-lessons-informed JSON extraction
# ---------------------------------------------------------------------------

def _extract_json_object(text):
    """Defensive JSON extraction, per the 203 incident report: don't assume the
    whole response is clean JSON -- strip code fences and pull the first {...}."""
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_classification(obj):
    """Coerce near-miss shapes instead of failing outright -- same philosophy as
    203's schema normalization layer (e.g. {"name": "Python"} -> "Python")."""
    if obj is None:
        return None
    divisions = obj.get("divisions", [])
    if isinstance(divisions, str):
        divisions = [divisions]
    normalized_divisions = []
    for d in divisions:
        if isinstance(d, dict):
            d = d.get("division") or d.get("name") or ""
        d = str(d).strip().lower()
        if d in DIVISIONS and d not in normalized_divisions:
            normalized_divisions.append(d)
    return {
        "divisions": normalized_divisions,
        "reasoning": str(obj.get("reasoning", "")).strip(),
        "summary": str(obj.get("summary", "")).strip(),
    }


def classify_document(client, text, max_chars=6000):
    """Classify which division(s) a document affects. Returns a normalized dict,
    or a dict with an 'error' key if the model never produced usable JSON after
    one retry -- callers should let the user pick divisions manually in that case."""
    excerpt = text[:max_chars]
    raw, tokens = generate(
        client, excerpt, system=CLASSIFY_SYSTEM, max_new_tokens=300, temperature=0.0,
    )
    result = _normalize_classification(_extract_json_object(raw))
    if result is None or not result["divisions"]:
        # One retry with a more forceful instruction, per the 203 report's finding
        # that models sometimes need to be told explicitly not to add prose.
        raw, tokens2 = generate(
            client,
            excerpt,
            system=CLASSIFY_SYSTEM + "\nReturn ONLY the JSON object. No other text at all.",
            max_new_tokens=300,
            temperature=0.0,
        )
        result = _normalize_classification(_extract_json_object(raw))
        tokens = {"in": tokens["in"] + tokens2["in"], "out": tokens["out"] + tokens2["out"]}
    if result is None or not result["divisions"]:
        return {"error": "Could not automatically classify this document. "
                          "Please select the affected division(s) manually.",
                "raw": raw, "tokens": tokens}
    result["tokens"] = tokens
    return result


# ---------------------------------------------------------------------------
# Cross-division impact snapshot
# ---------------------------------------------------------------------------

IMPACT_SYSTEM = (
    "You are Tanya, TGMOK Holdings' cross-division assistant. A new document has just "
    "arrived, filed under one or more divisions; it is note [1] below, with its own real "
    "id shown in parentheses like every other note. Using ONLY the notes provided (the "
    "new document plus retrieved notes from OTHER divisions, each \"[N] (doc_id) text\" "
    "-- doc_id is the code in parentheses, never the bracket number N), write a short "
    "brief for leadership: what does this new document say, and does anything in the "
    "other divisions' existing records look connected to it (e.g. related tooling, "
    "financing, shared clients)? If nothing in the other divisions' notes appears "
    "connected, say so plainly -- do not invent a connection. Finish with exactly one "
    "line: 'Cited: ' followed by the real id(s) you used, comma-separated. This is a "
    "FORMAT example only, with ids that do not exist in this corpus -- never reuse them, "
    "always substitute the real id(s) from the notes above: Cited: abc-01, xyz-02"
)


def generate_impact_snapshot(client, new_doc_text, new_doc_divisions, new_doc_ids, chunks, matrix, embedder, k=4):
    """Retrieve from divisions OTHER than the ones the new doc was filed under,
    using the new document's own text as the query, then ask the model to
    synthesize a cross-division impact brief. This is a demo aid for a human to
    read and judge -- it is NOT added to eval_questions.json as a scored case,
    since there is no pre-verified ground truth for a live-uploaded document.

    new_doc_ids: the real doc_id(s) the upload was just saved under (one per division
    in new_doc_divisions -- see app.py). Without a real, citable id here, the model has
    nothing valid to put in its citation for the document it is actually describing, and
    was observed echoing the prompt's literal placeholder text instead (see docs/ALIGNMENT.md)."""
    other_divisions = [d for d in DIVISIONS if d not in new_doc_divisions]
    query = new_doc_text[:1500]
    hits = retrieve(query, chunks, matrix, embedder, k=k, divisions=other_divisions or None)
    excerpt_id = new_doc_ids[0] if new_doc_ids else "new-upload"
    notes = [f"[1] ({excerpt_id}) {query[:400]}"]
    notes += [f"[{i+2}] ({h['doc_id']} · {h['division']}) {h['text']}" for i, h in enumerate(hits)]
    context = "\n\n".join(notes)
    snapshot, tokens = generate(client, context, system=IMPACT_SYSTEM, max_new_tokens=500)
    return snapshot, hits, tokens
