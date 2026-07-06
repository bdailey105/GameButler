# GameButler Decision Log

## D-2026-07-05-01 — Local/home-LAN remains the product target

**Status:** Accepted

GameButler is optimized for Bryan's personal local/home-LAN usage, not a multi-tenant public SaaS. This keeps the architecture simple: SQLite, Docker Compose, Nginx frontend proxy, and a single-user trust model.

**Implications:**

- Security hardening matters, but public internet auth is not the next priority.
- Backup/restore matters because the local SQLite DB is the source of personal curation.
- Global or single-process assumptions can be tolerated short-term if documented, but should not block local reliability.

## D-2026-07-05-02 — Deterministic recommender owns decisions

**Status:** Accepted

Recommendation ranking should be deterministic application logic. Optional LLM/local model features may explain, summarize, or add butler personality later, but should not be the source of truth for filtering, scoring, status changes, or persistence.

**Implications:**

- Scoring signals belong in Python tests.
- Explanations should initially be generated from scoring reasons, not freeform model output.
- Local LLM integration can be added as a presentation layer after deterministic explanations exist.

## D-2026-07-05-03 — Rich metadata comes before fancier recommendation UX

**Status:** Accepted

Persisting art/descriptions and making enrichment visible should come before mood buttons and advanced recommendations. This creates immediate user-visible improvement and establishes the schema patterns needed for later work.

**Implications:**

- E12 should happen before or alongside E13.
- E14/E15 can assume richer metadata exists but should not require it for correctness.

## D-2026-07-05-04 — Keep status vocabulary small

**Status:** Proposed

Avoid adding many statuses early. Prefer the current stable statuses plus optional tags/notes later. Too many statuses make recommendation and queue behavior ambiguous.

**Implications:**

- Add `paused`, `revisit_later`, or `not_interested` only when a concrete workflow needs them.
- User tags/notes may be better than enum growth.

## D-2026-07-06-01 — Adopt "The Launcher" visual direction

**Status:** Accepted

The visual design handoff in `docs/GameButler — Design Document.pdf` selects "The Launcher" as the UI foundation. Future frontend work should align with that direction: dark navy app shell, blue primary actions, compact game cards, status-specific accents, responsive mobile screens, and explicit empty/loading/skeleton states.

**Implications:**

- UI stories should include visual acceptance criteria from the design document, not only functional behavior.
- The rich metadata card work from E12 should be refined into the Launcher card system before larger UI expansions.
- E13, E15, E16, and E18 should reuse the same design tokens/components instead of adding one-off visual styles.
