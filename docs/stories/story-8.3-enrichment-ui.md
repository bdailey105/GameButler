# Story 8.3: Enrichment UI & Progress

**Epic:** Epic 8: Metadata Enrichment
**Priority:** Medium
**Status:** Planned

## Description
Provide a visual cue and control for the user to start the enrichment process.

## Technical Tasks
1.  **Button**:
    -   Add "Enrich Library" button to the Library view (next to Auto-Tag).
    -   Disable while `loading`.
2.  **Feedback**:
    -   Show a loading spinner or progress text ("Enriching...").
    -   Since the backend might take a while, maybe show a "Partial Success" message if it times out or finishes a batch.
3.  **Visuals**:
    -   If we added `header_image`, display it in the `GameCard`.

## Acceptance Criteria
-   User clicks "Enrich Library", and after a wait, the "Unknown" tags are replaced with real data.
