---
name: new-chapter
description: Scaffold a new story chapter (a Scene YAML) for The Man Who Counted visual novel. Use when adding a chapter of the book or a new narrative scene.
---

# New chapter

A chapter is **data**: one YAML scene under
`src/the_man_who_counted/content/chapters/`. No engine code is needed unless the
chapter introduces a brand-new puzzle (then also run `/new-puzzle`) or a new
background (then add a painter, step 4).

## Steps

1. Pick the next number and a slug, e.g. `01_the_thirty_five_camels.yaml`.
   Chapters are loaded by name (without `.yaml`) via `story.load_scene(...)`.
2. Create the file from the template below.
3. Add any new speakers to `src/the_man_who_counted/content/characters.yaml`.
4. Backgrounds are cairo painters in `engine/scenery.py`. Reuse `desert`,
   `caravan`, `baghdad`, `night` — or write a new `paint_<name>(cr, w, h, t)`
   (fractions of `w`/`h`, horizon ≈ 0.6h, `t` only for ambient motion; reuse the
   `_vertical_gradient`, `_stars`, `_dune`, `_crescent`, `_camel`, `_dome`,
   `_minaret` helpers) and add it to `SCENES`. Preview it by painting to a
   `cairo.ImageSurface` and saving a PNG.
5. If the chapter should be reachable from the menu, wire it up in `window.py`
   (currently `OPENING_CHAPTER = "00_prologue"`); continue/chapter-select is
   still to come.
6. Verify it loads and validates, then run the tests (they also check every
   `art:` name is painted):
   ```bash
   cd src && python3 -c "from the_man_who_counted.engine.story import load_scene; from the_man_who_counted.puzzles import puzzle_ids; print(load_scene('01_the_thirty_five_camels', known_puzzles=puzzle_ids()).title)"
   cd .. && python3 -m pytest
   ```
   then play it with `/play`.

## Template

```yaml
id: <slug>
title: "<Chapter Title Shown in the Header>"

beats:
  - art: <background-name>            # Optional opening background

  - narration: "Set the scene in the narrator's voice."
  - say: <character-id>
    text: "A line of dialogue."

  - choice: "What do you do?"
    options:
      - text: "First option"
        goto: path_a
      - text: "Second option"
        goto: path_b

  - label: path_a
  - narration: "..."
  - goto: trial

  - label: path_b
  - narration: "..."

  - label: trial
  - puzzle: <puzzle-id>              # Must exist in puzzles/__init__.py REGISTRY
    on_win: won
    on_lose: lost

  - label: won
  - narration: "The reward — the story moves forward."
  - goto: finish

  - label: lost
  - narration: "A gentler turn; the story still continues."

  - label: finish
  - end: "— Closing line —"
```

## Beat reference

- `narration:` / `say:`+`text:` — Text beats; optional `art:` and `speed:` (cps).
- `choice:`+`options:` (`text`,`goto`) — Branch to a `label`.
- `puzzle:`+`on_win`/`on_lose` — Hand off to a registered puzzle, branch on result.
- `art:` (+`transition: fade|cut`), `label:`, `goto:`, `end:`.

The loader validates labels and puzzle ids at load time and raises `StoryError`
on anything dangling — fix those before shipping the chapter.

## Style and rights

Standard English capitalization: sentence case for narration and dialogue,
title case for chapter titles. Keep the desert / Arabian Nights tone of the
source book. The player is Beremiz; the narrator is the Traveller.

Write **original prose** — never copy sentences from the book or its
translations (it is under copyright until 2045; see CLAUDE.md). Retell in our
own words; the math puzzles themselves are free to use.
