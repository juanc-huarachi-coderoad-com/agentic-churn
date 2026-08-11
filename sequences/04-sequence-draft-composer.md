# 04 · Sequence — Draft composer

Spec §12.3, M10. Traces `REQ-M10-*`. Ends with **no send** — the human takes the drafted text into their own tool.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as CS lead
    participant Ask as M9 · Ask agent
    participant Composer as M10 · Draft composer (LLM)
    participant Evidence as M6/M7 output (issue + evidence)
    participant Profile as M3 · Client profile (comm. norms)
    participant Checks as Automatic pre-display checks
    participant UI as Draft composer UI
    participant Collector as M1 · Email collector (later, external)

    User->>Ask: "Write to Ana about this"
    Ask->>Composer: Hand off: top issue reference (REQ-M9-02)

    Composer->>Evidence: Fetch top issue + cited events
    Composer->>Profile: Fetch communication norms, rhythm, language
    Composer->>Composer: Generate draft: acknowledge specifically first,\none ask, match rhythm, offer tone variants (REQ-M10-01..05)

    Composer->>Checks: Submit draft for validation
    Checks->>Checks: Every fact exists in evidence? (REQ-M10-07)
    Checks->>Checks: No invented dates? No internal leak? No other client mentioned?

    alt All checks pass
        Checks->>UI: Render draft beside its evidence
        UI-->>User: "Copy draft" / "Log to CRM" only — no send action exists (REQ-M10-08, REQ-M10-P1)
        User->>User: Pastes draft into own email client and sends (outside this system)
        User->>Collector: (external) Sent email lands back as a normal outbound event
        Collector->>Collector: Ledger append closes the response clock (REQ-M10-09)
    else Any check fails
        Checks->>UI: Block display — do not render the failing draft
    end
```

## Key invariant

There is no arrow in this diagram from the Draft composer UI to any client-facing transport (SMTP, chat API). The human-send step happens **outside the system boundary**, and only re-enters as a normal collected event once the human has already sent it through their own tool — matching product principle P4 exactly.
