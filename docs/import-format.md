# External Library Import Format

GameButler can import non-Steam games (Switch, PlayStation, Xbox, PC launchers,
retro, etc.) from a normalized CSV file. Steam games are not imported this way —
Steam has its own automatic sync (`/upload` and Steam Sync), so a row with
`platform=steam` is rejected as invalid.

## Columns

| Column             | Required | Notes                                                                 |
|---------------------|----------|------------------------------------------------------------------------|
| `title`             | yes      | Game name. Must be non-empty.                                          |
| `platform`          | yes      | One of the platform vocabulary below.                                  |
| `source`            | yes      | Free-text label for where the row came from, e.g. `nintendo_export`.   |
| `external_id`       | no       | ID within that source (e.g. a launcher's internal game ID).            |
| `genre`             | no       | Free-text genre.                                                       |
| `tags`              | no       | Free-text tags.                                                        |
| `playtime_minutes`  | no       | Total playtime in minutes. Must be numeric if present.                 |

Headers are matched case-insensitively and with surrounding whitespace stripped,
so `Title`, ` title `, and `title` are all accepted. Any missing required header
is reported by name so the fix is obvious.

## Platform vocabulary

- `switch`
- `playstation`
- `xbox`
- `pc`
- `retro`

`steam` is intentionally not part of this list — Steam games sync automatically
and importing them here would create a second, disconnected record.

## Example

```csv
title,platform,source,external_id,genre,tags,playtime_minutes
The Legend of Zelda: Tears of the Kingdom,switch,nintendo_export,70010000012345,Adventure,Open World,2400
Metroid Prime Remastered,switch,nintendo_export,70010000067890,Action,Platformer,540
Chrono Trigger,retro,personal_spreadsheet,,RPG,Classic,
```

## Matching rules

Each row is matched against your existing library so repeated imports update
the right record instead of creating duplicates:

1. If the row has an `external_id`, it's matched by `(source, external_id)`
   against existing games with that same source and external ID.
2. Otherwise, it's matched case-insensitively by `(title, platform)`.

Rows that match nothing become new games. Rows that match an existing game are
either **updated** (something would actually change) or **skipped** (nothing
new to add). Two rows in the same file that resolve to the same identity are
counted as **duplicates** — the first occurrence wins.

## Personal fields are never overwritten

Importing only ever touches identity and catalog metadata (`genre`, `tags`,
`playtime_minutes`, `source`, `external_id`, `platform`). By default it also
only *fills in* metadata that's currently missing, `Unknown`, or zero — it
never clobbers a value you've already set, unless you explicitly opt into
`replace_metadata=true` on import.

The following fields are never touched by import, no matter what:

- `status`
- `attention_level`
- `personal_rating`
- `current_note` / journal entries
- `session_tags`
- `return_when`

## Preview before you commit

`POST /import/external/preview` runs the same parsing and classification as a
real import but writes nothing — it reports counts of new, updated, skipped,
and duplicate rows, plus a list of invalid rows with actionable error messages
(bad platform, empty title, non-numeric playtime). Use it to sanity-check a
file before calling `POST /import/external`.
