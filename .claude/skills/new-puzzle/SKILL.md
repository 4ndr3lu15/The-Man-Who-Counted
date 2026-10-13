---
name: new-puzzle
description: Scaffold a new bespoke puzzle page for The Man Who Counted visual novel and register it. Use when adding a hand-crafted puzzle from the book.
---

# New puzzle

Puzzles are **artisanal**, not instances of a generic template — each one is
designed by hand to fit its moment in the story. This skill only removes the
boilerplate (the page shell + registration); the actual design is done with
the user.

## The only contract

A puzzle is an `Adw.NavigationPage` with a `"finished"` signal that it emits
**once** with a `PuzzleResult(won=..., detail="...")` from
`the_man_who_counted.engine.director`. The stage pushes the page, pops it on
`finished`, and the director branches the story on `result.won`.

Reuse the palette (gold `#D4AF37`, navy `#0b1320`/`#101c30`, pale gold
`#F3E5AB`) and standard capitalization (title case for titles and buttons, sentence case for messages). Keep any pure rules in a separate UI-free module
(like `game.py`) so they can be unit-tested — that's how the balance puzzle is
structured; follow it. Custom drawing goes in a `Gtk.DrawingArea` with cairo
(see `puzzles/scale_view.py`); motion via `Adw.TimedAnimation` /
`Adw.SpringAnimation`.

## Steps

1. Create `src/the_man_who_counted/puzzles/<name>.py` from the template below.
2. Register it in `src/the_man_who_counted/puzzles/__init__.py` (lazy, by name —
   keeps the registry GTK-free for the story tests):
   ```python
   REGISTRY = {
       "balance": ("balance", "BalancePuzzlePage"),
       "<id>": ("<name>", "<Name>PuzzlePage"),
   }
   ```
3. Reference `<id>` from a chapter's `puzzle:` beat (see `/new-chapter`).
4. If there are pure rules, add `tests/test_<name>.py`.
5. Add its keys to `shortcuts_dialog()` in `window.py` if it has shortcuts.
6. Verify with `/play` (reach it from a chapter, or push `make_puzzle("<id>")`
   onto `window.navigation` from the drive script).

## Template

```python
"""<one-line description of the puzzle and its place in the book>."""

from __future__ import annotations

from gi.repository import Adw, GObject, Gtk

from ..engine.director import PuzzleResult


class <Name>PuzzlePage(Adw.NavigationPage):
    __gtype_name__ = "Tmwc<Name>PuzzlePage"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self) -> None:
        # The story waits on this page, so there is no going back mid-trial.
        super().__init__(title="The Trial of ...", tag="puzzle", can_pop=False)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12,
                       margin_bottom=18, margin_start=18, margin_end=18)
        # ... Bespoke, hand-crafted UI for this puzzle ...
        submit = Gtk.Button(label="Submit", css_classes=["pill", "suggested-action"],
                            halign=Gtk.Align.CENTER)
        submit.connect("clicked", lambda _b: self._submit())
        body.append(submit)

        toolbar = Adw.ToolbarView(content=Adw.Clamp(maximum_size=900, child=body),
                                  css_classes=["puzzle"])
        toolbar.add_top_bar(Adw.HeaderBar(css_classes=["flat"]))
        self.set_child(toolbar)

    def _submit(self) -> None:
        won = self._check()  # Your win condition
        result = PuzzleResult(won=won, detail="...")
        dialog = Adw.AlertDialog(heading="✦ The Sultan Is Pleased ✦" if won else "✦ The Sultan Frowns ✦",
                                 body=result.detail)
        dialog.add_response("continue", "Continue ▸")
        dialog.set_response_appearance("continue", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_close_response("continue")
        dialog.connect("response", lambda _d, _r: self.emit("finished", result))
        dialog.present(self)

    def _check(self) -> bool:
        raise NotImplementedError
```

Guard against finishing twice (e.g. a `_done` flag that disables input after the
result), as `balance.py` does — the stage expects exactly one `finished`.
