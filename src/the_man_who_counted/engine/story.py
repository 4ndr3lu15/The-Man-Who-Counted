"""The story data model and YAML loader.

A *chapter* on disk is a YAML file describing one :class:`Scene`: an ordered list
of *beats*. The engine walks the beats in order; ``choice`` and ``puzzle`` beats
can branch to a named ``label``. Keeping the story as data (not code) is what
makes adding the book chapter by chapter cheap: write a YAML file, pick or paint
a background, done.

This module has no UI and no dependency on the puzzle implementations, so it is
fully unit-testable. Puzzle ids are validated against a caller-supplied set so
the loader stays decoupled from :mod:`the_man_who_counted.puzzles`.

Example chapter::

    id: prologue
    title: "On the Road to Baghdad"
    beats:
      - narration: "The sun hung low over the desert..."
        art: desert
      - say: beremiz
        text: "I was counting the grains of sand."
      - puzzle: balance
        on_win: praised
        on_lose: doubted
      - label: praised
      - narration: "The sultan smiled."
      - label: doubted
      - end: "— End of the prologue —"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from typing import Any, Iterable

import yaml

NARRATOR = "narrator"


class StoryError(Exception):
    """Raised when a chapter file is malformed or references something missing."""


# -- characters -------------------------------------------------------------
@dataclass(frozen=True)
class Character:
    """A speaking character: how their name appears and in what colour."""

    id: str
    name: str
    color: str = "#E0E0E0"
    art: str | None = None


# -- beats ------------------------------------------------------------------
@dataclass
class Beat:
    """Base class for everything that can happen in a scene."""


@dataclass
class Narration(Beat):
    text: str
    art: str | None = None
    speed: float | None = None


@dataclass
class Say(Beat):
    speaker: str
    text: str
    art: str | None = None
    speed: float | None = None


@dataclass
class ChoiceOption:
    text: str
    goto: str


@dataclass
class Choice(Beat):
    prompt: str
    options: list[ChoiceOption]


@dataclass
class Puzzle(Beat):
    id: str
    on_win: str | None = None
    on_lose: str | None = None


@dataclass
class Art(Beat):
    art: str
    transition: str = "fade"


@dataclass
class Label(Beat):
    name: str


@dataclass
class Goto(Beat):
    target: str


@dataclass
class End(Beat):
    text: str | None = None


# -- scene ------------------------------------------------------------------
@dataclass
class Scene:
    id: str
    title: str
    beats: list[Beat]
    characters: dict[str, Character] = field(default_factory=dict)
    labels: dict[str, int] = field(default_factory=dict)

    def index_of_label(self, name: str) -> int:
        try:
            return self.labels[name]
        except KeyError as exc:
            raise StoryError(f"unknown label: {name!r}") from exc

    def character(self, speaker: str) -> Character:
        """Look up a speaker, falling back to a plain default if undefined."""
        if speaker in self.characters:
            return self.characters[speaker]
        return Character(id=speaker, name=speaker)


# -- pure flow helpers (unit-testable, no UI) -------------------------------
def next_index(scene: Scene, current: int) -> int | None:
    """The index of the beat after ``current`` in linear flow, or None at the end."""
    nxt = current + 1
    return nxt if nxt < len(scene.beats) else None


def resolve_branch(scene: Scene, label: str | None, current: int) -> int | None:
    """Where to go after a branching beat.

    ``label`` jumps to that named label; ``None`` falls through to the next beat.
    """
    if label is None:
        return next_index(scene, current)
    return scene.index_of_label(label)


# -- loading ----------------------------------------------------------------
def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if key not in mapping:
        raise StoryError(f"{where}: missing required key {key!r}")
    return mapping[key]


def _parse_beat(raw: dict[str, Any], n: int) -> Beat:
    where = f"beat #{n}"
    if not isinstance(raw, dict):
        raise StoryError(f"{where}: each beat must be a mapping, got {type(raw).__name__}")

    if "narration" in raw:
        return Narration(text=raw["narration"], art=raw.get("art"), speed=raw.get("speed"))
    if "say" in raw:
        return Say(
            speaker=raw["say"],
            text=_require(raw, "text", where),
            art=raw.get("art"),
            speed=raw.get("speed"),
        )
    if "choice" in raw:
        options = [
            ChoiceOption(text=_require(o, "text", f"{where} option"), goto=_require(o, "goto", f"{where} option"))
            for o in _require(raw, "options", where)
        ]
        if not options:
            raise StoryError(f"{where}: choice needs at least one option")
        return Choice(prompt=raw["choice"], options=options)
    if "puzzle" in raw:
        return Puzzle(id=raw["puzzle"], on_win=raw.get("on_win"), on_lose=raw.get("on_lose"))
    if "art" in raw:
        return Art(art=raw["art"], transition=raw.get("transition", "fade"))
    if "label" in raw:
        return Label(name=raw["label"])
    if "goto" in raw:
        return Goto(target=raw["goto"])
    if "end" in raw:
        # ``end:`` may carry a closing line or be an empty marker.
        text = raw["end"]
        return End(text=text if isinstance(text, str) and text else None)

    raise StoryError(f"{where}: unrecognised beat keys {sorted(raw)}")


def parse_scene(
    data: dict[str, Any],
    characters: dict[str, Character] | None = None,
    *,
    known_puzzles: Iterable[str] | None = None,
) -> Scene:
    """Build and validate a :class:`Scene` from parsed YAML data."""
    scene_id = _require(data, "id", "scene")
    title = _require(data, "title", "scene")
    raw_beats = _require(data, "beats", "scene")
    if not isinstance(raw_beats, list) or not raw_beats:
        raise StoryError("scene: 'beats' must be a non-empty list")

    beats = [_parse_beat(raw, i) for i, raw in enumerate(raw_beats)]
    labels = {b.name: i for i, b in enumerate(beats) if isinstance(b, Label)}

    scene = Scene(
        id=scene_id,
        title=title,
        beats=beats,
        characters=dict(characters or {}),
        labels=labels,
    )
    _validate(scene, known_puzzles)
    return scene


def _validate(scene: Scene, known_puzzles: Iterable[str] | None) -> None:
    puzzles = set(known_puzzles) if known_puzzles is not None else None
    for i, beat in enumerate(scene.beats):
        if isinstance(beat, Choice):
            for opt in beat.options:
                if opt.goto not in scene.labels:
                    raise StoryError(f"beat #{i}: choice goes to unknown label {opt.goto!r}")
        elif isinstance(beat, Goto):
            if beat.target not in scene.labels:
                raise StoryError(f"beat #{i}: goto target unknown label {beat.target!r}")
        elif isinstance(beat, Puzzle):
            for label in (beat.on_win, beat.on_lose):
                if label is not None and label not in scene.labels:
                    raise StoryError(f"beat #{i}: puzzle branches to unknown label {label!r}")
            if puzzles is not None and beat.id not in puzzles:
                raise StoryError(
                    f"beat #{i}: unknown puzzle id {beat.id!r} (known: {sorted(puzzles)})"
                )


def load_characters(package: str = "the_man_who_counted") -> dict[str, Character]:
    """Load the shared character roster from ``content/characters.yaml``."""
    text = resources.files(package).joinpath("content/characters.yaml").read_text("utf-8")
    data = yaml.safe_load(text) or {}
    roster: dict[str, Character] = {}
    for cid, attrs in (data.get("characters") or {}).items():
        attrs = attrs or {}
        roster[cid] = Character(
            id=cid,
            name=attrs.get("name", cid),
            color=attrs.get("color", "#E0E0E0"),
            art=attrs.get("art"),
        )
    return roster


def load_scene(
    chapter: str,
    *,
    package: str = "the_man_who_counted",
    known_puzzles: Iterable[str] | None = None,
) -> Scene:
    """Load and validate a chapter from ``content/chapters/<chapter>.yaml``."""
    path = resources.files(package).joinpath(f"content/chapters/{chapter}.yaml")
    try:
        text = path.read_text("utf-8")
    except FileNotFoundError as exc:
        raise StoryError(f"no such chapter: {chapter!r}") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise StoryError(f"chapter {chapter!r}: top level must be a mapping")
    return parse_scene(data, load_characters(package), known_puzzles=known_puzzles)
