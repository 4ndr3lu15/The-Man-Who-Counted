"""Tests for the story model, loader, validation, and flow helpers."""

import pytest

from the_man_who_counted.engine import story
from the_man_who_counted.engine.story import (
    Choice,
    End,
    Narration,
    Puzzle,
    Say,
    StoryError,
    next_index,
    parse_scene,
    resolve_branch,
)
from the_man_who_counted.puzzles import puzzle_ids


# -- the shipped prologue ---------------------------------------------------
def test_prologue_loads_and_validates():
    scene = story.load_scene("00_prologue", known_puzzles=puzzle_ids())
    assert scene.id == "prologue"
    assert scene.beats
    # It references the balance puzzle and branches on win/lose.
    puzzles = [b for b in scene.beats if isinstance(b, Puzzle)]
    assert len(puzzles) == 1
    assert puzzles[0].id == "balance"
    assert puzzles[0].on_win in scene.labels
    assert puzzles[0].on_lose in scene.labels


def test_prologue_speakers_resolve_to_characters():
    scene = story.load_scene("00_prologue", known_puzzles=puzzle_ids())
    beremiz = scene.character("beremiz")
    assert beremiz.name == "Beremiz Samir"
    assert beremiz.color.startswith("#")


# -- parsing & validation ---------------------------------------------------
SIMPLE = {
    "id": "t",
    "title": "test",
    "beats": [
        {"narration": "hello", "art": "desert"},
        {"say": "beremiz", "text": "hi"},
        {"puzzle": "balance", "on_win": "good", "on_lose": "bad"},
        {"label": "good"},
        {"narration": "won"},
        {"goto": "fin"},
        {"label": "bad"},
        {"narration": "lost"},
        {"label": "fin"},
        {"end": "done"},
    ],
}


def test_parse_scene_builds_beats_and_labels():
    scene = parse_scene(SIMPLE, known_puzzles={"balance"})
    assert isinstance(scene.beats[0], Narration)
    assert isinstance(scene.beats[1], Say)
    assert isinstance(scene.beats[-1], End)
    assert set(scene.labels) == {"good", "bad", "fin"}


def test_unknown_puzzle_id_rejected():
    with pytest.raises(StoryError):
        parse_scene(SIMPLE, known_puzzles={"not_balance"})


def test_choice_to_unknown_label_rejected():
    bad = {
        "id": "t",
        "title": "t",
        "beats": [
            {"choice": "?", "options": [{"text": "a", "goto": "nowhere"}]},
        ],
    }
    with pytest.raises(StoryError):
        parse_scene(bad)


def test_goto_to_unknown_label_rejected():
    bad = {"id": "t", "title": "t", "beats": [{"goto": "nowhere"}]}
    with pytest.raises(StoryError):
        parse_scene(bad)


def test_say_requires_text():
    bad = {"id": "t", "title": "t", "beats": [{"say": "beremiz"}]}
    with pytest.raises(StoryError):
        parse_scene(bad)


# -- flow helpers -----------------------------------------------------------
def test_next_index_stops_at_end():
    scene = parse_scene(SIMPLE, known_puzzles={"balance"})
    assert next_index(scene, 0) == 1
    assert next_index(scene, len(scene.beats) - 1) is None


def test_resolve_branch_jumps_or_falls_through():
    scene = parse_scene(SIMPLE, known_puzzles={"balance"})
    # The puzzle beat is index 2; on_win 'good' is a label.
    win_target = resolve_branch(scene, "good", 2)
    assert win_target == scene.labels["good"]
    # None means linear fall-through to the next beat.
    assert resolve_branch(scene, None, 2) == 3


def test_choice_parses_options():
    data = {
        "id": "t",
        "title": "t",
        "beats": [
            {"choice": "pick", "options": [{"text": "x", "goto": "h"}]},
            {"label": "h"},
        ],
    }
    scene = parse_scene(data)
    choice = scene.beats[0]
    assert isinstance(choice, Choice)
    assert choice.options[0].goto == "h"
