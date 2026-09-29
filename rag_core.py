"""The whole retrieval-and-answer pipeline, shared by the app (app.py), the evaluation
(harness.py) and the regression demo (demo_citation_fix.py), so every reported number describes
the pipeline the app actually runs.

    load_corpus -> build_chunks -> build_index (embed) -> retrieve -> answer_question
    classify_document -> format_upload_content -> generate_impact_snapshot     (uploads)

Reads the fixed, hand-verified corpus in data/<division>/ and writes only to data/uploads/,
which the evaluation never reads. Settings come from config.py; the code-side mitigations
(citation checks, confidence hand-off, token cap, injection scan and strip) live in guardrails.py.

This is a workflow, not an agent (Class 4): the code fixes every step, the model is called once
per question, and it has no tools, so it can write text for a person and nothing else.

Upload classification asks for JSON defensively: an explicit schema, a generous token budget
(reasoning models can silently truncate), regex extraction rather than trusting the whole reply
to be clean JSON, and normalising near-miss shapes instead of failing outright.
"""
import json
import re

import numpy as np

from config import (ABSTAIN_BELOW, CHUNK_WORDS, DATA_DIR, DIVISIONS, EMBED_MODEL, GEN_MODEL,
                    OVERLAP, PATH_TO_DOC_ID, ROOT, TITLED_EMBEDDING, TOP_K, UPLOADS_DIR)
from guardrails import handoff_message, strip_instructions

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

    Fixed documents get the ids in config.DOC_ID_TO_PATH (fnb-01 ... jwl-06), the same ids the
    answer key, the evaluation, the notebook and the docs use, so a citation in the app can be
    checked against results/ without translating between two naming schemes.

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
                rel = f.relative_to(DATA_DIR).as_posix()
                docs.append({
                    "doc_id": PATH_TO_DOC_ID.get(rel, f.stem),  # unregistered files keep their
                    "division": division,                       # stem; data/check_my_data.py flags them
                    "path": f.relative_to(ROOT).as_posix(),
                    "text": f.read_text(encoding="utf-8"),
                    "source": "fixed",
                })
        upload_dir = UPLOADS_DIR / division
        if upload_dir.exists():
            for f in sorted(upload_dir.glob("*.md")):
                docs.append({
                    "doc_id": f"upload-{division}-{f.stem}",
                    "division": division,
                    "path": f.relative_to(ROOT).as_posix(),
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
        title = doc_title(d)
        for c in chunk(d["text"]):
            chunks.append({"text": c, "doc_id": d["doc_id"], "division": d["division"], "title": title})
    return chunks


def doc_title(d):
    """A document's "# Title" line. Every fixed document has one (hand-authored convention); an
    upload usually won't, so this falls back to the doc_id rather than raising."""
    return next((ln[2:].strip() for ln in d["text"].splitlines() if ln.startswith("# ")), d["doc_id"])


def embed_text(c):
    """The string actually embedded for retrieval matching -- the chunk's own document title
    prepended to its text, when config.TITLED_EMBEDDING is on (what the app ships). Measured in
    results/retrieval_recall.md (`titled_k5` against `naive_k5`): division recall 91% -> 100%,
    average document recall unchanged at 88% -- titling fixes which DIVISION is covered, not
    which DOCUMENT. The text shown to the model and checked for citations (h['text']) is
    unchanged: only what similarity is computed against changes, so it costs no extra
    generation tokens."""
    return f"{c['title']}. {c['text']}" if TITLED_EMBEDDING else c["text"]


def build_index(docs=None):
    """chunks, embedding matrix and embedder for a corpus, built the one way the app ships.
    The app, the regression demo and the evaluation's `shipped` config all go through here, so
    none of them can quietly embed differently from the others."""
    docs = load_corpus() if docs is None else docs
    chunks = build_chunks(docs)
    texts = [embed_text(c) for c in chunks]
    embedder = Embedder(texts)
    return docs, chunks, embedder.embed(texts), embedder


class Embedder:
    """Local sentence-transformers embeddings, TF-IDF fallback -- same pattern as
    the notebook. Built once per Streamlit session and cached in session_state.

    If the fallback fires, `using` says so: the keyword baseline and the main system would then
    both be TF-IDF, and any comparison between them would be meaningless. Every report prints
    `using` for that reason."""

    def __init__(self, chunk_texts):
        self.using = None
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBED_MODEL)
            self.using = f"local embeddings ({EMBED_MODEL.split('/')[-1]}) -- matches MEANING"
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


def format_notes(hits, start=1):
    """The numbered notes block every answer prompt carries: "[N] (doc_id) text". The one place it
    is built, so the app, the evaluation and the cost estimate send identical prompts.

    Each note's text first passes guardrails.strip_instructions: a sentence addressed to the model
    (say, in an upload a person filed despite the scan) is replaced by a visible marker, and what
    was removed is recorded on the hit as h["removed"] for the app to show. Notes with no such
    sentence, which is every note in the fixed corpus, are sent unchanged."""
    lines = []
    for i, h in enumerate(hits, start):
        text, h["removed"] = strip_instructions(h["text"])
        lines.append(f"[{i}] ({h['doc_id']}) {text}")
    return "\n\n".join(lines)


def answer_question(client, question, chunks, matrix, embedder, k=TOP_K, divisions=None,
                    abstain_below=ABSTAIN_BELOW):
    hits = retrieve(question, chunks, matrix, embedder, k=k, divisions=divisions)
    if abstain_below is not None and hits and hits[0]["score"] < abstain_below:
        return handoff_message(hits[0]["score"], abstain_below), hits, {"in": 0, "out": 0}
    context = format_notes(hits)
    answer, tokens = generate(client, f"NOTES:\n{context}\n\nQUESTION: {question}", system=GROUNDED)
    return answer, hits, tokens


# ---------------------------------------------------------------------------
# Document classification -- defensive JSON extraction
# ---------------------------------------------------------------------------

def _extract_json_object(text):
    """Defensive JSON extraction: don't assume the whole response is clean JSON --
    strip code fences and pull the first {...}."""
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
    """Coerce near-miss shapes instead of failing outright (e.g. {"division": "fnb"}
    inside the list -> "fnb", a bare string -> a one-item list)."""
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
        # One retry with a more forceful instruction: models sometimes need to be told
        # explicitly not to add prose around the JSON.
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
    result["raw"] = raw   # the model's exact reply, before parsing: the app shows it beside the parsed result
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
    read and judge -- it is NOT added to data/eval_questions.json as a scored case,
    since there is no pre-verified ground truth for a live-uploaded document.

    new_doc_ids: the real doc_id(s) the upload was just saved under (one per division
    in new_doc_divisions -- see app.py). Without a real, citable id here, the model has
    nothing valid to put in its citation for the document it is actually describing, and
    was observed echoing the prompt's literal placeholder text instead ("Cited: <doc_id>", the
    bug in the screen recordings; regression check: demo_citation_fix.py)."""
    other_divisions = [d for d in DIVISIONS if d not in new_doc_divisions]
    query = new_doc_text[:1500]
    hits = retrieve(query, chunks, matrix, embedder, k=k, divisions=other_divisions or None)
    excerpt_id = new_doc_ids[0] if new_doc_ids else "new-upload"
    # The upload itself is untrusted text too: the scan at upload time warned the person, and this
    # strips the same sentences from what the model reads (see format_notes).
    excerpt, _ = strip_instructions(query[:400])
    notes = [f"[1] ({excerpt_id}) {excerpt}"]
    for i, h in enumerate(hits):
        text, h["removed"] = strip_instructions(h["text"])
        notes.append(f"[{i+2}] ({h['doc_id']} · {h['division']}) {text}")
    context = "\n\n".join(notes)
    snapshot, tokens = generate(client, context, system=IMPACT_SYSTEM, max_new_tokens=500)
    return snapshot, hits, tokens
