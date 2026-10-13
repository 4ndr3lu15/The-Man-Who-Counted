"""Tests for the director: the story flow, driven without any UI."""

from the_man_who_counted.engine import director, story
from the_man_who_counted.engine.director import (
    AskChoice,
    PuzzleResult,
    RunPuzzle,
    SetArt,
    ShowEnd,
    ShowText,
)
from the_man_who_counted.engine.story import parse_scene
from the_man_who_counted.puzzles import puzzle_ids

BRANCHY = {
    "id": "t",
    "title": "test",
    "beats": [
        {"art": "desert", "transition": "cut"},
        {"narration": "hello", "art": "caravan"},
        {"choice": "which way?", "options": [{"text": "a", "goto": "a"}, {"text": "b", "goto": "b"}]},
        {"label": "a"},
        {"say": "beremiz", "text": "path a"},
        {"goto": "trial"},
        {"label": "b"},
        {"say": "beremiz", "text": "path b"},
        {"label": "trial"},
        {"puzzle": "balance", "on_win": "won", "on_lose": "lost"},
        {"label": "won"},
        {"narration": "won"},
        {"goto": "fin"},
        {"label": "lost"},
        {"narration": "lost"},
        {"label": "fin"},
        {"end": "the end"},
    ],
}


def run(scene, answers):
    """Drive the director, answering choices/puzzles from ``answers``; return the commands seen."""
    flow = director.play(scene)
    seen = []
    answer = None
    answers = list(answers)
    while True:
        try:
            command = flow.send(answer)
        except StopIteration:
            return seen
        seen.append(command)
        answer = answers.pop(0) if isinstance(command, (AskChoice, RunPuzzle)) else None


def texts(commands):
    return [c.text for c in commands if isinstance(c, ShowText)]


def scene():
    return parse_scene(BRANCHY, story.load_characters(), known_puzzles={"balance"})


def test_linear_start_sets_art_then_narrates():
    commands = run(scene(), ["a", PuzzleResult(won=True)])
    assert commands[0] == SetArt("desert", "cut")
    assert commands[1] == SetArt("caravan")
    assert commands[2] == ShowText(None, director.NARRATOR_COLOR, "hello")


def test_choice_and_win_branch():
    commands = run(scene(), ["a", PuzzleResult(won=True)])
    assert texts(commands) == ["hello", "path a", "won"]
    assert isinstance(commands[-1], ShowEnd) and commands[-1].text == "the end"


def test_other_choice_and_lose_branch():
    commands = run(scene(), ["b", PuzzleResult(won=False)])
    assert texts(commands) == ["hello", "path b", "lost"]


def test_say_uses_character_name_and_colour():
    commands = run(scene(), ["a", PuzzleResult(won=True)])
    line = next(c for c in commands if isinstance(c, ShowText) and c.text == "path a")
    assert line.name == "Beremiz Samir"
    assert line.color == "#D4AF37"


def test_non_result_puzzle_answer_is_coerced():
    # A puzzle handing back a bare truthy value still counts as a win.
    assert texts(run(scene(), ["a", True]))[-1] == "won"


def test_prologue_plays_through_both_ways():
    prologue = story.load_scene("00_prologue", known_puzzles=puzzle_ids())
    for choice in ("companion", "skeptic"):
        for won in (True, False):
            commands = run(prologue, [choice, PuzzleResult(won=won)])
            assert sum(isinstance(c, RunPuzzle) for c in commands) == 1
            assert isinstance(commands[-1], ShowEnd)
