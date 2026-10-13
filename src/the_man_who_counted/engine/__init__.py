"""The visual-novel engine: story model, director, stage page, and animated widgets.

The engine is deliberately content-agnostic. It knows how to *tell* a story —
reveal narration with a typewriter, cross-fade painted backgrounds, show a
speaker's dialogue, offer choices, and hand off to a bespoke puzzle page — but it
knows nothing about any particular chapter. Chapters live as data in
``content/`` and puzzles live as hand-crafted pages in ``puzzles/``.

``story``, ``director`` and ``anim`` are pure Python (no GTK) and unit-tested;
``scenery`` needs only cairo; ``widgets`` and ``novel_page`` are the GTK view.
"""
