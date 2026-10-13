"""Bespoke puzzle pages, registered by id.

Each puzzle is a *hand-crafted* piece of game design — not an instance of some
generic template. The only contract the engine imposes is: a puzzle is an
``Adw.NavigationPage`` with a ``"finished"`` signal that it emits, once, with a
:class:`~the_man_who_counted.engine.director.PuzzleResult`. The stage pushes the
page, pops it again on ``finished``, and the director branches the story on
``result.won``.

To add a puzzle: build its page module, then register it here under a short id,
and reference that id from a chapter's ``puzzle:`` beat. The ``/new-puzzle``
skill scaffolds the boilerplate.

The registry names modules lazily so that :func:`puzzle_ids` (used to validate
chapters) never imports GTK — the story tests stay display-free.
"""

from __future__ import annotations

from importlib import import_module

# Puzzle id -> (module inside this package, page class name).
REGISTRY: dict[str, tuple[str, str]] = {
    "balance": ("balance", "BalancePuzzlePage"),
}


def puzzle_ids() -> set[str]:
    """Ids known to the registry — used to validate chapter files at load time."""
    return set(REGISTRY)


def make_puzzle(puzzle_id: str):
    """Build a fresh puzzle page registered under ``puzzle_id``."""
    try:
        module_name, class_name = REGISTRY[puzzle_id]
    except KeyError as exc:
        raise KeyError(f"unknown puzzle id: {puzzle_id!r} (known: {sorted(REGISTRY)})") from exc
    module = import_module(f".{module_name}", __name__)
    return getattr(module, class_name)()
