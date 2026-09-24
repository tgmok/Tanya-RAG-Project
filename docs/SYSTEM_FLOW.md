# Tanya · system flow

How the Streamlit demo (`webapp/app.py`) routes a request, and how TGMOK Holdings'
three divisions are connected in the underlying corpus.

## Request flow

Two entry points converge on the same retrieval-and-answer path. Uploading a
document is optional -- a user can go straight to asking a question.

```mermaid
flowchart TD
    START([User opens Tanya]) --> CHOICE{Upload a document,<br/>or ask directly?}

    CHOICE -->|upload PDF/DOCX/TXT| EXTRACT["extract_text()<br/>pypdf / python-docx"]
    EXTRACT --> CLASSIFY["classify_document()<br/>LLM call -> divisions + reasoning + summary"]
    CLASSIFY --> PARSEOK{Valid JSON<br/>returned?}
    PARSEOK -->|no, even after retry| MANUAL["User picks division(s)<br/>manually via checkboxes"]
    PARSEOK -->|yes| SUGGEST["Suggested division(s)<br/>pre-checked for user to confirm/edit"]
    MANUAL --> CONFIRM{User confirms}
    SUGGEST --> CONFIRM
    CONFIRM -->|cancel| CHOICE
    CONFIRM -->|confirm| FILE["Write .md into<br/>data/uploads/&lt;division&gt;/"]
    FILE --> REBUILD["rebuild_index()<br/>re-chunk + re-embed corpus"]
    REBUILD --> SNAPSHOT["generate_impact_snapshot()<br/>retrieve from OTHER divisions using<br/>the new doc's own text as the query"]
    SNAPSHOT --> SHOW["Show snapshot + cited notes<br/>(a demo aid for a human to judge --<br/>not a scored eval case)"]
    SHOW --> CHAT

    CHOICE -->|ask directly| CHAT["Chat box: user types a question"]
    CHAT --> RETRIEVE["retrieve()<br/>embed question, top-k chunks<br/>across the current corpus"]
    RETRIEVE --> GROUNDED["generate() with the GROUNDED prompt<br/>answer ONLY from retrieved notes"]
    GROUNDED --> ABSTAIN{Notes contain<br/>the answer?}
    ABSTAIN -->|no| DECLINE["'The documents do not say.'"]
    ABSTAIN -->|yes| CITE["Answer + 'Cited: &lt;doc_id, ...&gt;'"]
    DECLINE --> CHAT
    CITE --> CHAT
```

## Why the upload path never touches the graded corpus

`data/fnb/`, `data/cnc/`, `data/jewellery/` are the fixed, hand-verified corpus
that `eval_questions.json`'s 23 questions were written against, per the
watch-outs' "fix the ground truth before you run anything." A live upload has no
pre-verified answer, so it's filed into a separate `data/uploads/<division>/`
tree instead -- the retrieval index includes it once confirmed, but it never
becomes a new scored eval case.

## How the three divisions are connected

The fixed corpus was built around three deliberate cross-division "hooks" (see
`generation_prompts.md`), each split across two or more divisions' documents so
that a single-division answer is necessarily incomplete:

```mermaid
flowchart LR
    subgraph FNB["F&B · Contract Manufacturing"]
        FNB1["packaging_change_sop.md"]
        FNB2["client_contract_summary.md<br/>(Aurora Beverages rush order)"]
        FNB4["maintenance_log.md"]
        FNB6["financial_summary_q3.md"]
    end

    subgraph CNC["CNC · Precision Machine Parts"]
        CNC1["tooling_spec_bottle_cap.md"]
        CNC2["capacity_planning_report.md"]
        CNC4["material_procurement_policy.md"]
        CNC6["client_order_backlog.md"]
    end

    subgraph JWL["Jewellery · Manufacturing & Retail"]
        JWL1["finance_intercompany_loan_report.md"]
        JWL2["gold_pricing_policy.md"]
    end

    FNB1 -- "H1: packaging change<br/>requires new tooling" --> CNC1
    FNB4 -- "H1: tooling installed on<br/>the filling line" --> CNC1

    FNB2 -- "H3: rush order forces<br/>capacity reprioritisation" --> CNC2
    CNC2 -- "H3: external client order<br/>delayed as a result" --> CNC6

    JWL1 -- "H2: intercompany financing<br/>extended to F&B" --> FNB6
    JWL1 -- "H2: intercompany financing<br/>extended to CNC" --> CNC4

    JWL2 -. "custom stamping die<br/>sourced from CNC (non-hook)" .-> CNC6
```

A question that only retrieves from one division in a hook pair will always be
incomplete -- this is exactly what Section 7's context-recall metric measures,
and what the notebook's naive-vs-filtered "break it" comparison demonstrates
directly (see `Tanya_RAG_Notebook.ipynb`, section 9).
