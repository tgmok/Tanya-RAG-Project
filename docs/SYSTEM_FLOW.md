# Tanya · system flow

How the app (`app.py`) routes a request, where each built guardrail (`guardrails.py`) sits on
that path, and how TGMOK Holdings' three divisions are connected in the underlying corpus.

It is a workflow, not an agent (Class 4): the code fixes every step, the model is called once per
question, and it has no tools, so the only thing it can produce is text a person reads. The one
write in the system, filing an upload, waits for a person to confirm.

## Request flow

Two entry points converge on the same retrieval-and-answer path. Uploading a document is
optional -- a user can go straight to asking a question. Every rounded box marked **G** is code,
not prompt, and is exercised against named cases by `python run_guardrails.py`
(`results/guardrails.md`).

```mermaid
flowchart TD
    START([User opens Tanya]) --> CHOICE{Upload a document,<br/>or ask directly?}

    CHOICE -->|upload PDF/DOCX/TXT| EXTRACT["doc_parser.extract_text()<br/>pypdf / python-docx, no model"]
    EXTRACT --> SCAN(["G2 scan_for_injection()<br/>OWASP LLM01:2026"])
    SCAN -->|phrase matched| MANUAL["Person picks division(s) by hand;<br/>matched phrases shown"]
    SCAN -->|clean| CAP1(["G1 session token cap<br/>OWASP LLM06:2026"])
    CAP1 --> CLASSIFY["rag_core.classify_document()<br/>LLM call: divisions + reasoning + summary"]
    CLASSIFY --> PARSEOK{Valid JSON,<br/>even after one retry?}
    PARSEOK -->|no| MANUAL
    PARSEOK -->|yes| SUGGEST["Suggested division(s)<br/>pre-checked for the person to confirm/edit"]
    MANUAL --> CONFIRM{"Person confirms<br/>(nothing is written before this)"}
    SUGGEST --> CONFIRM
    CONFIRM -->|cancel| CHOICE
    CONFIRM -->|confirm| FILE["format_upload_content() adds 'Filed under: ...';<br/>write .md into data/uploads/&lt;division&gt;/"]
    FILE --> REBUILD["rag_core.build_index()<br/>re-chunk + re-embed"]
    REBUILD --> SNAPSHOT["generate_impact_snapshot()<br/>retrieve from OTHER divisions using<br/>the new document's own text as the query;<br/>every note stripped as in G8"]
    SNAPSHOT --> FIG1(["G5 unsupported_figures()<br/>confabulation check"])
    FIG1 --> SHOW["Brief + cited notes + a warning if any figure<br/>is not in a cited document (read by a person,<br/>not a scored case)"]
    SHOW --> CHAT

    CHOICE -->|ask directly| CHAT["Chat box: a question"]
    CHAT --> RETRIEVE["rag_core.retrieve()<br/>top-5, title-prefixed embedding,<br/>over the current corpus"]
    RETRIEVE --> HAND(["G3 best score below 0.45?"])
    HAND -->|yes| PERSON["'The documents do not say.' +<br/>handed to a person -- NO model call"]
    HAND -->|no| CAP2(["G1 session token cap"])
    CAP2 --> STRIP(["G8 format_notes: strip any sentence<br/>addressed to the model; warn the reader<br/>OWASP LLM01 / LLM09:2026"])
    STRIP --> GROUNDED["generate() with the GROUNDED prompt:<br/>answer ONLY from the numbered notes"]
    GROUNDED --> ABSTAIN{Notes contain<br/>the answer?}
    ABSTAIN -->|no| DECLINE["'The documents do not say.'"]
    ABSTAIN -->|yes| CITE["Answer + 'Cited: fnb-01, cnc-01'<br/>(real ids, never bracket numbers),<br/>shown with the notes it drew on"]
    CITE --> FIG2(["G5 unsupported_figures()"])
    FIG2 --> CHAT
    DECLINE --> CHAT
    PERSON --> CHAT
```

## Why the upload path never touches the graded corpus

`data/fnb/`, `data/cnc/`, `data/jewellery/` are the fixed, hand-verified corpus that
`data/eval_questions.json`'s 23 questions were written against, per the watch-outs' "fix the
ground truth before you run anything." A live upload has no pre-verified answer, so it is filed
into a separate `data/uploads/<division>/` tree instead -- the app's index includes it once a
person confirms it, but git ignores that folder and the evaluation never reads it, so nothing
done in the app can move a reported number.

## How the three divisions are connected

The fixed corpus was built around three deliberate cross-division "hooks" (see
`data/generation_prompts.md`), each split across two or more divisions' documents so that a
single-division answer is necessarily incomplete:

```mermaid
flowchart LR
    subgraph FNB["F&B · Contract Manufacturing"]
        FNB1["fnb-01 packaging_change_sop"]
        FNB2["fnb-02 client_contract_summary<br/>(Aurora Beverages rush order)"]
        FNB4["fnb-04 maintenance_log"]
        FNB6["fnb-06 financial_summary_q3"]
    end

    subgraph CNC["CNC · Precision Machine Parts"]
        CNC1["cnc-01 tooling_spec_bottle_cap"]
        CNC2["cnc-02 capacity_planning_report"]
        CNC4["cnc-04 material_procurement_policy"]
        CNC6["cnc-06 client_order_backlog"]
    end

    subgraph JWL["Jewellery · Manufacturing & Retail"]
        JWL1["jwl-01 finance_intercompany_loan_report"]
        JWL2["jwl-02 gold_pricing_policy"]
    end

    FNB1 -- "H1: packaging change<br/>requires new tooling" --> CNC1
    FNB4 -- "H1: tooling installed on<br/>the filling line" --> CNC1

    FNB2 -- "H3: rush order forces<br/>capacity reprioritisation" --> CNC2
    CNC2 -- "H3: external client order<br/>delayed as a result" --> CNC6

    JWL1 -- "H2: intercompany financing<br/>extended to F&B" --> FNB6
    JWL1 -- "H2: intercompany financing<br/>extended to CNC" --> CNC4

    JWL2 -. "custom stamping die<br/>sourced from CNC (non-hook)" .-> CNC6
```

A question that only retrieves from one division in a hook pair will always be incomplete --
this is what the context-recall metric measures. The shipped retrieval covers every
needed division on all 11 cross-division questions, but still misses a needed *document* on 5 of
37 scored questions; three of those are the same CNC tooling spec, `cnc-01`, diagnosed in the
notebook's "break it" section (`results/retrieval_recall.md` lists every miss).
