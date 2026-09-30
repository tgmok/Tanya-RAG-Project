"""Tanya's guardrails: every risk mitigation that is code, not prompt.

A mitigation you only describe is not a mitigation, so each one below is a function the app or
the evaluation actually calls, and run_guardrails.py exercises every one of them against named
cases (results/guardrails.md). No model calls here, no network.

OWASP numbers follow the Top 10 for LLM Applications, 2026 edition, as taught in Class 6 (they
differ from the 2025 edition's). The silent failure is named with NIST AI 600-1's word for it,
confabulation: confidently stated erroneous content.

  risk                                                  guard (this file)          where it runs
  ----------------------------------------------------  -------------------------  ------------------------
  confabulation: a fluent answer with an invented       unsupported_figures()      app, every answer;
    figure, date or id (NIST AI 600-1)                                             evaluation, every answer
  fake citation dressed up as grounding (the bug in     malformed_citation()       evaluation; regression demo
    the screen recordings)
  citing a document the model was not given (the new   citations_not_given()      app, every answer and
    failure in the final evaluation)                                               upload brief
  answering when retrieval found nothing relevant       handoff_message() via      app + evaluation, before
                                                        rag_core.answer_question   any model call
  unbounded spend in one session                        session_tokens_exceeded()  app, before every model call
    (LLM06:2026 Unbounded Consumption)
  instructions hidden in an uploaded document           scan_for_injection()       app, before the one
    (LLM01:2026 Prompt Injection)                                                  automatic model call on raw
                                                                                   upload text
  instructions inside a note that reaches the answer    strip_instructions() via   app + evaluation, every
    prompt: an upload a person filed anyway (LLM01:2026  rag_core.format_notes      prompt that carries notes
    indirect; LLM09:2026 Vector & Embedding Weaknesses,
    the write path into the store)
  recognising an abstention, exactly                    is_abstention()            app + evaluation

Human confirmation before an upload is filed is the remaining built mitigation; it is interface
flow, so it lives in app.py (the upload is never written until a person picks the divisions).
"""
import re

from config import ABSTAIN_PHRASE, MAX_SESSION_TOKENS


# ---------------------------------------------------------------------------
# Unbounded consumption (OWASP LLM06:2026)
# ---------------------------------------------------------------------------

def session_tokens_exceeded(tokens_in, tokens_out, cap=MAX_SESSION_TOKENS):
    """Stop the session loudly rather than spending without limit. The app checks this before
    every model call and refuses the call once the cap is reached."""
    return (tokens_in + tokens_out) >= cap


# ---------------------------------------------------------------------------
# Prompt injection in uploaded documents (OWASP LLM01:2026)
# ---------------------------------------------------------------------------

# Uploaded documents are untrusted input: the classifier reads the raw upload text with an LLM
# call, so a phrase aimed at that model rather than at the reader is a real risk. This is a
# code-side SCAN, not a filter -- it never edits the text or blocks the upload; it routes the
# document to manual division selection instead of the automatic classifier call, and shows the
# user exactly what matched. False positives are expected (a real SOP can legitimately contain
# the word "instructions"); that is the accepted cost of a cheap, auditable check.
INJECTION_PATTERNS = [
    r"ignore (?:the )?(?:previous|prior|above|all) instructions",
    r"disregard (?:the )?(?:previous|prior|above) instructions",
    r"new instructions\s*:",
    r"system prompt",
    r"you are now",
    # "act as an auditor" is fine, other roleplay is flagged. The article sits INSIDE the lookahead:
    # written as `act as (?:a |an )?(?!auditor\b)`, the optional article could be skipped and the
    # lookahead then saw "an auditor", so the exemption never applied (caught by run_guardrails.py).
    r"act as (?!(?:a |an )?auditor\b)",
    r"reveal (?:your|the) (?:prompt|instructions|system message)",
    r"\bDAN\b",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def scan_for_injection(text):
    """Return the distinct matched phrases (as they appear in the text), or [] if none."""
    return list(dict.fromkeys(m.group(0) for m in _INJECTION_RE.finditer(text or "")))


# The same patterns, applied a second time: to every note just before it goes into a prompt. The
# upload scan above only routes a suspicious document to a person, and a person can still file it,
# after which its text is retrievable into ANY later answer (Class 6: LLM09:2026, "treat anything a
# third party put in the store as untrusted text -- which is row 1 again").
#
# This is a tripwire, not the defence. OWASP's own text is that no reliable prevention for LLM01
# exists, and an attacker can rephrase around any pattern list. What makes a successful injection
# survivable here is architecture: Tanya has no tools and no outbound channel (two legs of the
# lethal trifecta, not three), and every answer is a draft a person reads. What this adds is
# visibility: the sentence is removed as the course's strip_instructions() removes a line, the
# removal is recorded on the note, and the app tells the reader it happened.
REMOVED_MARK = "[removed by Tanya: a sentence addressed to the model]"
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")


def strip_instructions(text):
    """Return (text with every sentence that matches an injection pattern replaced by
    REMOVED_MARK, the removed sentences). Text with no match comes back unchanged, byte for byte,
    so on the fixed corpus (no matches; run_guardrails.py checks every chunk) the prompts the
    evaluation measured are exactly the prompts the app sends."""
    if not _INJECTION_RE.search(text or ""):
        return text, []
    kept, removed = [], []
    for sentence in _SENTENCE_BREAK.split(text):
        if _INJECTION_RE.search(sentence):
            removed.append(sentence.strip())
            kept.append(REMOVED_MARK)
        elif sentence.strip():
            kept.append(sentence)
    return " ".join(kept), removed


# ---------------------------------------------------------------------------
# Abstention and the confidence hand-off
# ---------------------------------------------------------------------------

def is_abstention(answer):
    return "do not say" in (answer or "").lower()


def handoff_message(top_score, threshold):
    """What the user sees when retrieval confidence is below the threshold. No model is called:
    the question goes to a person. Contains the exact abstention phrase, so every downstream check
    treats it as an abstention."""
    return (f"{ABSTAIN_PHRASE} [Low retrieval confidence: the best match scored {top_score:.2f}, below "
            f"{threshold:.2f}, so this question is passed to a human reviewer instead of being answered.]")


# ---------------------------------------------------------------------------
# Citation checks: the silent-failure detectors
# ---------------------------------------------------------------------------

def cited_doc_ids(answer, known_ids):
    m = re.search(r"cited:\s*(.+)$", answer or "", re.I | re.S)
    if not m:
        return set()
    tail = m.group(1).lower()
    return {d for d in known_ids if d.lower() in tail}


_CITED_ID = re.compile(r"upload-[a-z]+-[\w-]+|\b[a-z]{3}-\d{2}\b")


def citations_not_given(answer, given_ids):
    """The ids in an answer's 'Cited:' line that were NOT among the notes the model was given, in the
    order cited. Catches the failure the final evaluation found: the notes mention another document by
    its code (QC-FNB-002, POL-CNC-005), and the model cites that document as if it had read it (CD2,
    CD11, S4), or cites an id that does not exist at all (CD12's 'cnc-07'). [] when every citation was
    given, or when nothing is cited (an honest decline). The app shows a warning, so the reader knows
    which citation, and anything it supports, is unverified."""
    m = re.search(r"cited:\s*(.+)$", answer or "", re.I | re.S)
    if not m:
        return []
    given = {g.lower() for g in given_ids}
    out = []
    for cid in _CITED_ID.findall(m.group(1).lower()):
        if cid not in given and cid not in out:
            out.append(cid)
    return out


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
    """Code check that a cited document really contains the figures in the answer (the
    citation-verification mitigation). Returns the numbers, dates and ids in the answer that appear
    in NONE of the cited documents; [] if all are supported; None if the answer abstains or cites
    no known document (nothing to verify against).

    Known limit, measured in round 11 of testing: it catches invented FIGURES, not an invented
    claim with nothing numeric in it ("installed immediately", a component name borrowed from an
    unrelated document). That residual confabulation risk is named in docs/TRADEOFF_ANALYSIS.md."""
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
