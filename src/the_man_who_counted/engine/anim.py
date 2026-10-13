"""Pure, UI-free animation helpers.

These functions hold the *math* of the engine's animations so the timing logic
can be unit-tested without a running GTK app. The widgets in
:mod:`the_man_who_counted.engine.widgets` apply these results to frame-clock tick
callbacks and ``Adw.TimedAnimation`` values.

Keeping them pure also means an animation never depends on wall-clock state it
cannot see: given the same inputs you always get the same frame.
"""

from __future__ import annotations

# Default reveal speed for the typewriter, in characters per second.
DEFAULT_CPS = 45.0


def typewriter_index(elapsed: float, total_chars: int, cps: float = DEFAULT_CPS) -> int:
    """How many characters should be visible after ``elapsed`` seconds.

    The result is clamped to ``[0, total_chars]`` so callers can use it directly
    as a slice end. ``cps`` is characters-per-second; a non-positive ``cps``
    reveals everything at once (useful for "instant" / reduced-motion modes).
    """
    if total_chars <= 0:
        return 0
    if cps <= 0 or elapsed < 0:
        return total_chars if elapsed >= 0 and cps <= 0 else 0
    return min(total_chars, int(elapsed * cps))


def is_typewriter_done(elapsed: float, total_chars: int, cps: float = DEFAULT_CPS) -> bool:
    """True once the typewriter has revealed every character."""
    return typewriter_index(elapsed, total_chars, cps) >= total_chars


def frame_index(tick: int, frame_count: int) -> int:
    """Index into a looping animation of ``frame_count`` frames for a given tick.

    Wraps around forever; ``tick`` is simply a monotonically increasing counter
    incremented by a timer. Returns 0 when there are no frames.
    """
    if frame_count <= 0:
        return 0
    return tick % frame_count


def ease_in_out(t: float) -> float:
    """Smoothstep easing on a normalized ``t`` in ``[0, 1]``.

    Endpoints are exact (``0 -> 0``, ``1 -> 1``); values outside the range are
    clamped. Used for hand-rolled fades drawn with cairo.
    """
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from ``a`` to ``b`` by eased fraction ``t``."""
    return a + (b - a) * ease_in_out(t)
