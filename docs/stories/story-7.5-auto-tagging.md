# Story 7.5: Basic Auto-Tagging (Heuristic)

**Epic:** Epic 7: Backlog Management & Attention Tracking
**Priority:** Low
**Status:** Planned

## Description
To reduce manual effort, the system should guess the attention level based on Steam tags when importing games.

## Technical Tasks
1.  **Define Heuristics**: Create a mapping dictionary in Python.
    -   **Casual Tags**: "Arcade", "Casual", "Puzzle", "Clicker", "Idler", "Card Game".
    -   **Focused Tags**: "Story Rich", "RPG", "Strategy", "Visual Novel", "Simulation", "Horror".
2.  **Update Import Logic**:
    -   In `src/data_loader.py` (or wherever the import happens), iterating through the CSV rows.
    -   If `attention_level` is unset, check tags against heuristics.
    -   Assign `casual` or `focused` if a match is found.
    -   (Conflict resolution: If matches both, maybe default to Focused or leave Unset).
3.  **Endpoint**: Optional "Run Auto-Tagging" admin endpoint if we want to re-run it on existing data.

## Acceptance Criteria
-   Importing a new library automatically populates `attention_level` for obvious candidates (e.g., "Cookie Clicker" -> Casual, "The Witcher 3" -> Focused).
-   Manual overrides are respected (if I manually set it, auto-tagging shouldn't overwrite it on next sync, unless forced).
