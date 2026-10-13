"""The director: walks a scene's beats and tells the stage what to do.

The director is a plain Python *generator*. It yields small command objects
(``SetArt``, ``ShowText``, ``AskChoice``, ``RunPuzzle``, ``ShowEnd``) and the
stage (:class:`~the_man_who_counted.engine.novel_page.NovelPage`) performs each one and
``send()``s back the answer once the player has acted: ``None`` for text, the
chosen label for a choice, a :class:`PuzzleResult` for a puzzle.

That keeps the whole story flow free of GTK — it can be driven step by step in
a unit test with scripted answers — while the stage stays a thin view that just
reacts to commands on the GLib main loop. The branching *math* lives in
:mod:`the_man_who_counted.engine.story` (``resolve_branch``/``index_of_label``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generator

from . import story
from .story import Art, Choice, ChoiceOption, End, Goto, Narration, Puzzle, Say, Scene

NARRATOR_COLOR = "#A0A0A0"


@dataclass(frozen=True)
class PuzzleResult:
    """What a bespoke puzzle page hands back to the story.

    Puzzles finish with one of these; the director branches on :attr:`won`.
    ``detail`` is free-form so a puzzle can pass a flavour string back into the
    narration later if we want it.
    """

    won: bool
    detail: str = ""


# -- commands the director yields to the stage -------------------------------
@dataclass(frozen=True)
class SetArt:
    """Change the background. Needs no answer."""

    art: str
    transition: str = "fade"


@dataclass(frozen=True)
class ShowText:
    """Reveal a line; answer ``None`` once the player advances."""

    name: str | None
    color: str
    text: str
    speed: float | None = None


@dataclass(frozen=True)
class AskChoice:
    """Offer options; answer with the chosen option's ``goto`` label."""

    prompt: str
    options: tuple[ChoiceOption, ...]


@dataclass(frozen=True)
class RunPuzzle:
    """Hand off to a registered puzzle; answer with a :class:`PuzzleResult`."""

    puzzle_id: str


@dataclass(frozen=True)
class ShowEnd:
    """The closing line; answer ``None`` once the player leaves."""

    text: str | None


Command = SetArt | ShowText | AskChoice | RunPuzzle | ShowEnd


def play(scene: Scene) -> Generator[Command, Any, None]:
    """Walk ``scene`` from its first beat, yielding commands for the stage."""
    i: int | None = 0
    while i is not None and 0 <= i < len(scene.beats):
        beat = scene.beats[i]

        if isinstance(beat, Narration):
            if beat.art:
                yield SetArt(beat.art)
            yield ShowText(None, NARRATOR_COLOR, beat.text, beat.speed)
            i = story.next_index(scene, i)

        elif isinstance(beat, Say):
            if beat.art:
                yield SetArt(beat.art)
            who = scene.character(beat.speaker)
            yield ShowText(who.name, who.color, beat.text, beat.speed)
            i = story.next_index(scene, i)

        elif isinstance(beat, Art):
            yield SetArt(beat.art, beat.transition)
            i = story.next_index(scene, i)

        elif isinstance(beat, Choice):
            goto = yield AskChoice(beat.prompt, tuple(beat.options))
            i = scene.index_of_label(goto)

        elif isinstance(beat, Puzzle):
            result = yield RunPuzzle(beat.id)
            if not isinstance(result, PuzzleResult):  # Defensive: truthy means a win
                result = PuzzleResult(won=bool(result))
            label = beat.on_win if result.won else beat.on_lose
            i = story.resolve_branch(scene, label, i)

        elif isinstance(beat, Goto):
            i = scene.index_of_label(beat.target)

        elif isinstance(beat, End):
            yield ShowEnd(beat.text)
            return

        else:  # Label, or an unknown beat: skip rather than crash a play session.
            i = story.next_index(scene, i)
