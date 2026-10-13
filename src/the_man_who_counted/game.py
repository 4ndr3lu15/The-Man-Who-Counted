"""Pure game logic for Malba Tahan.

No user interface lives here — only the rules of the puzzle. That keeps the
mechanic trivially testable and lets the GTK app stay a thin view layer.

The puzzle:
    There are 8 gold balls. All look identical, but exactly one is slightly
    heavier. Using a balance scale at most twice, find the heavy one.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

TOTAL_BALLS = 8
MAX_WEIGHINGS = 2
NORMAL_WEIGHT = 10
HEAVY_BONUS = 1


class Location(str, Enum):
    """Where a ball currently sits."""

    STAGING = "staging"
    LEFT = "left"
    RIGHT = "right"


class GameError(Exception):
    """Raised when an action is not allowed by the current game state."""


class Tilt(int, Enum):
    """Which way the beam tips after a weighing."""

    LEFT = -1
    LEVEL = 0
    RIGHT = 1


@dataclass
class Game:
    """The full state of one round of the riddle."""

    total_balls: int = TOTAL_BALLS
    max_weighings: int = MAX_WEIGHINGS

    heavy_ball: int = field(init=False)
    weighings_taken: int = field(init=False)
    locations: dict[int, Location] = field(init=False)
    last_tilt: Tilt | None = field(init=False)
    over: bool = field(init=False)
    won: bool | None = field(init=False)

    def __post_init__(self) -> None:
        self.new_game()

    # -- lifecycle ----------------------------------------------------------
    def new_game(self, *, rng: random.Random | None = None) -> None:
        """Start a fresh round, choosing a new (hidden) heavy ball."""
        chooser = rng or random
        self.heavy_ball = chooser.randrange(self.total_balls)
        self.weighings_taken = 0
        self.locations = {i: Location.STAGING for i in range(self.total_balls)}
        self.last_tilt = None
        self.over = False
        self.won = None

    # -- queries ------------------------------------------------------------
    @property
    def weighings_left(self) -> int:
        return self.max_weighings - self.weighings_taken

    def balls_in(self, location: Location) -> list[int]:
        return [b for b, loc in self.locations.items() if loc == location]

    def pan_counts(self) -> tuple[int, int]:
        return len(self.balls_in(Location.LEFT)), len(self.balls_in(Location.RIGHT))

    def can_weigh(self) -> bool:
        if self.over or self.weighings_left <= 0:
            return False
        left, right = self.pan_counts()
        return left > 0 and left == right

    # -- mutations ----------------------------------------------------------
    def place(self, ball: int, location: Location) -> None:
        """Move a ball to staging, the left pan, or the right pan."""
        if self.over:
            raise GameError("The round is already over.")
        if ball not in self.locations:
            raise GameError(f"No such ball: {ball}")
        self.locations[ball] = location

    def clear_pans(self) -> None:
        """Send every ball on the scale back to the staging area."""
        for ball in self.balls_in(Location.LEFT) + self.balls_in(Location.RIGHT):
            self.locations[ball] = Location.STAGING

    def weigh(self) -> Tilt:
        """Perform a weighing and return which way the beam tips.

        Raises GameError unless ``can_weigh()`` is true.
        """
        if self.over:
            raise GameError("The round is already over.")
        if self.weighings_left <= 0:
            raise GameError("No weighings left — you must identify the heavy ball.")
        if not self.can_weigh():
            raise GameError("Both pans need the same number of balls (at least one).")

        left_weight = self._pan_weight(Location.LEFT)
        right_weight = self._pan_weight(Location.RIGHT)

        self.weighings_taken += 1
        if left_weight > right_weight:
            self.last_tilt = Tilt.LEFT
        elif right_weight > left_weight:
            self.last_tilt = Tilt.RIGHT
        else:
            self.last_tilt = Tilt.LEVEL
        return self.last_tilt

    def guess(self, ball: int) -> bool:
        """Make the final guess. Ends the round; returns True on a win."""
        if self.over:
            raise GameError("The round is already over.")
        if ball not in self.locations:
            raise GameError(f"No such ball: {ball}")
        self.won = ball == self.heavy_ball
        self.over = True
        return self.won

    # -- internals ----------------------------------------------------------
    def _pan_weight(self, location: Location) -> int:
        balls = self.balls_in(location)
        weight = len(balls) * NORMAL_WEIGHT
        if self.heavy_ball in balls:
            weight += HEAVY_BONUS
        return weight
