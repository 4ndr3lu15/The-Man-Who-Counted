"""Tests for the pure game logic."""

import random

import pytest

from the_man_who_counted.game import Game, GameError, Location, Tilt


def make_game(heavy: int) -> Game:
    """Build a game with a deterministic heavy ball."""
    rng = random.Random(0)
    game = Game()
    game.new_game(rng=rng)
    game.heavy_ball = heavy
    return game


def test_new_game_resets_state():
    game = make_game(3)
    assert game.weighings_taken == 0
    assert all(loc is Location.STAGING for loc in game.locations.values())
    assert not game.over
    assert game.weighings_left == game.max_weighings


def test_cannot_weigh_empty_or_unequal():
    game = make_game(0)
    assert not game.can_weigh()
    game.place(0, Location.LEFT)
    assert not game.can_weigh()  # Unequal counts
    with pytest.raises(GameError):
        game.weigh()


def test_weigh_detects_heavier_side():
    game = make_game(0)  # Ball 0 is heavy
    game.place(0, Location.LEFT)
    game.place(1, Location.RIGHT)
    assert game.can_weigh()
    assert game.weigh() is Tilt.LEFT
    assert game.weighings_taken == 1


def test_weigh_level_when_heavy_ball_absent():
    game = make_game(7)  # Heavy ball stays in staging
    game.place(0, Location.LEFT)
    game.place(1, Location.RIGHT)
    assert game.weigh() is Tilt.LEVEL


def test_weighing_limit_enforced():
    game = make_game(0)
    for _ in range(game.max_weighings):
        game.place(0, Location.LEFT)
        game.place(1, Location.RIGHT)
        game.weigh()
        game.clear_pans()
    assert game.weighings_left == 0
    assert not game.can_weigh()
    with pytest.raises(GameError):
        game.weigh()


def test_clear_pans_returns_balls():
    game = make_game(0)
    game.place(0, Location.LEFT)
    game.place(1, Location.RIGHT)
    game.clear_pans()
    assert game.pan_counts() == (0, 0)


def test_correct_guess_wins_and_ends():
    game = make_game(4)
    assert game.guess(4) is True
    assert game.over and game.won
    with pytest.raises(GameError):
        game.guess(1)


def test_wrong_guess_loses():
    game = make_game(4)
    assert game.guess(2) is False
    assert game.over and game.won is False
