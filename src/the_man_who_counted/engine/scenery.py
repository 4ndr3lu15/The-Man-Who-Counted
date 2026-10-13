"""Painted backgrounds for the stage, drawn with cairo.

This replaces the terminal version's ascii art. Each scene is a *painter*: a
function ``paint(cr, w, h, t)`` that draws the whole background into a cairo
context of size ``w`` x ``h`` at time ``t`` (seconds — used only for gentle
ambient motion such as twinkling stars or a flickering lantern).

Painters are resolution-independent: every coordinate is a fraction of the
canvas, with the horizon kept around 60% of the height so the dialogue box at
the bottom of the stage never hides the interesting part.

To add a background: write a painter and register it in :data:`SCENES`, then
reference its name from a chapter's ``art:`` key. Unknown names fall back to a
plain night sky rather than crashing a play session.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from typing import Callable

import cairo

Painter = Callable[["cairo.Context", float, float, float], None]


# -- colour helpers ---------------------------------------------------------
def rgb(hex_color: str) -> tuple[float, float, float]:
    """``"#D4AF37"`` -> ``(0.83, 0.69, 0.22)``."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # Type: ignore[return-value]


GOLD = rgb("#D4AF37")
PALE_GOLD = rgb("#F3E5AB")
NAVY = rgb("#0b1320")


def _vertical_gradient(cr, h: float, stops: list[tuple[float, str]]) -> None:
    grad = cairo.LinearGradient(0, 0, 0, h)
    for offset, color in stops:
        grad.add_color_stop_rgb(offset, *rgb(color))
    cr.set_source(grad)
    cr.paint()


# -- stars ------------------------------------------------------------------
@lru_cache(maxsize=None)
def _star_field(seed: int, count: int) -> tuple[tuple[float, float, float, float, float], ...]:
    """Deterministic stars as ``(x, y, radius, phase, speed)`` in unit space."""
    rng = random.Random(seed)
    return tuple(
        (rng.random(), rng.random() ** 1.6, rng.uniform(0.6, 1.7), rng.uniform(0, math.tau), rng.uniform(0.6, 2.2))
        for _ in range(count)
    )


def _stars(cr, w: float, h: float, t: float, *, seed: int, count: int, max_y: float,
           alpha: float = 0.9, drift: float = 0.0) -> None:
    for x, y, r, phase, speed in _star_field(seed, count):
        px = ((x * w - t * drift) % w) if drift else x * w
        py = y * h * max_y
        twinkle = 0.55 + 0.45 * math.sin(t * speed + phase)
        cr.set_source_rgba(*PALE_GOLD, alpha * twinkle * (1.0 - y * 0.6))
        cr.arc(px, py, r, 0, math.tau)
        cr.fill()


# -- celestial bodies -------------------------------------------------------
def _glow(cr, cx: float, cy: float, r: float, color: tuple[float, float, float], alpha: float) -> None:
    grad = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    grad.add_color_stop_rgba(0.0, *color, alpha)
    grad.add_color_stop_rgba(1.0, *color, 0.0)
    cr.set_source(grad)
    cr.arc(cx, cy, r, 0, math.tau)
    cr.fill()


def _crescent(cr, cx: float, cy: float, r: float) -> None:
    _glow(cr, cx, cy, r * 3.2, PALE_GOLD, 0.12)
    cr.push_group()
    cr.set_source_rgb(*PALE_GOLD)
    cr.arc(cx, cy, r, 0, math.tau)
    cr.fill()
    cr.set_operator(cairo.OPERATOR_CLEAR)
    cr.arc(cx + r * 0.42, cy - r * 0.18, r * 0.86, 0, math.tau)
    cr.fill()
    cr.pop_group_to_source()
    cr.paint()


# -- terrain ----------------------------------------------------------------
def _dune(cr, w: float, h: float, base: float, amp: float, freq: float, phase: float, color: str,
          alpha: float = 1.0) -> None:
    """A smooth band of dunes from ``base`` (fraction of h) down to the bottom."""
    cr.move_to(0, h)
    steps = 64
    for i in range(steps + 1):
        x = w * i / steps
        u = i / steps
        y = h * (base - amp * (0.6 * math.sin(u * math.tau * freq + phase)
                               + 0.4 * math.sin(u * math.tau * freq * 2.3 + phase * 1.7)))
        cr.line_to(x, y)
    cr.line_to(w, h)
    cr.close_path()
    cr.set_source_rgba(*rgb(color), alpha)
    cr.fill()


def _dune_height(w: float, h: float, x: float, base: float, amp: float, freq: float, phase: float) -> float:
    u = x / w
    return h * (base - amp * (0.6 * math.sin(u * math.tau * freq + phase)
                              + 0.4 * math.sin(u * math.tau * freq * 2.3 + phase * 1.7)))


# -- figures ----------------------------------------------------------------
def _camel(cr, x: float, y: float, s: float, color: tuple[float, float, float], *, rider: bool = False,
           stride: float = 0.0) -> None:
    """A camel silhouette facing right; (x, y) is where its feet meet the ground."""
    cr.save()
    cr.translate(x, y)
    cr.scale(s, s)
    cr.set_source_rgb(*color)
    # Legs (pairs swing slightly in opposite directions)
    cr.set_line_width(0.05)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for lx, sw in ((-0.30, stride), (-0.20, -stride), (0.18, -stride), (0.28, stride)):
        cr.move_to(lx, -0.48)
        cr.line_to(lx + sw * 0.08, 0.0)
        cr.stroke()
    # Body and hump
    cr.save(); cr.translate(-0.02, -0.55); cr.scale(0.40, 0.17); cr.arc(0, 0, 1, 0, math.tau); cr.restore()
    cr.fill()
    cr.save(); cr.translate(-0.06, -0.70); cr.scale(0.20, 0.17); cr.arc(0, 0, 1, math.pi, math.tau); cr.restore()
    cr.fill()
    # Neck and head
    cr.move_to(0.28, -0.62)
    cr.curve_to(0.42, -0.60, 0.44, -0.80, 0.50, -0.95)
    cr.line_to(0.58, -0.95)
    cr.curve_to(0.54, -0.78, 0.50, -0.55, 0.34, -0.46)
    cr.close_path()
    cr.fill()
    cr.save(); cr.translate(0.60, -0.96); cr.scale(0.11, 0.055); cr.arc(0, 0, 1, 0, math.tau); cr.restore()
    cr.fill()
    # Tail
    cr.set_line_width(0.025)
    cr.move_to(-0.41, -0.58)
    cr.curve_to(-0.47, -0.50, -0.46, -0.42, -0.48, -0.36)
    cr.stroke()
    if rider:
        cr.move_to(-0.16, -0.84)
        cr.line_to(0.04, -0.84)
        cr.line_to(-0.04, -1.16)
        cr.close_path()
        cr.fill()
        cr.arc(-0.04, -1.20, 0.055, 0, math.tau)
        cr.fill()
    cr.restore()


def _dome(cr, cx: float, base: float, r: float) -> None:
    """An onion dome sitting on a drum, with a little spire."""
    cr.rectangle(cx - r * 0.9, base - r * 0.5, r * 1.8, r * 0.5)
    cr.fill()
    top = base - r * 0.5
    cr.move_to(cx - r, top)
    cr.curve_to(cx - r * 1.15, top - r * 0.9, cx - r * 0.2, top - r * 1.2, cx, top - r * 1.75)
    cr.curve_to(cx + r * 0.2, top - r * 1.2, cx + r * 1.15, top - r * 0.9, cx + r, top)
    cr.close_path()
    cr.fill()
    cr.rectangle(cx - r * 0.03, top - r * 2.1, r * 0.06, r * 0.4)
    cr.fill()


def _minaret(cr, cx: float, base: float, height: float, width: float) -> None:
    cr.rectangle(cx - width / 2, base - height, width, height)
    cr.fill()
    # Balcony
    cr.rectangle(cx - width * 0.85, base - height * 0.72, width * 1.7, width * 0.35)
    cr.fill()
    # Cap
    top = base - height
    cr.move_to(cx - width * 0.65, top)
    cr.curve_to(cx - width * 0.6, top - width * 0.9, cx, top - width * 1.2, cx, top - width * 2.2)
    cr.curve_to(cx, top - width * 1.2, cx + width * 0.6, top - width * 0.9, cx + width * 0.65, top)
    cr.close_path()
    cr.fill()


def _window_lights(cr, xs: list[tuple[float, float]], size: float, t: float) -> None:
    for i, (x, y) in enumerate(xs):
        flicker = 0.65 + 0.35 * math.sin(t * (1.3 + (i % 5) * 0.37) + i * 2.1)
        cr.set_source_rgba(*GOLD, 0.85 * flicker)
        cr.rectangle(x - size / 2, y - size, size, size * 1.6)
        cr.fill()


# -- the scenes -------------------------------------------------------------
def paint_night(cr, w: float, h: float, t: float) -> None:
    """The fallback: a clear desert night."""
    _vertical_gradient(cr, h, [(0.0, "#070d18"), (0.55, "#0b1320"), (1.0, "#16233b")])
    _stars(cr, w, h, t, seed=11, count=140, max_y=0.75)
    _dune(cr, w, h, 0.80, 0.03, 1.2, 0.4, "#111b2e")
    _dune(cr, w, h, 0.88, 0.025, 1.7, 2.0, "#0a111f")


def paint_title(cr, w: float, h: float, t: float) -> None:
    """The title screen: drifting stars over a moonlit desert."""
    _vertical_gradient(cr, h, [(0.0, "#060b15"), (0.6, "#0b1320"), (1.0, "#1b2740")])
    _stars(cr, w, h, t, seed=7, count=160, max_y=0.85, drift=6.0)
    _crescent(cr, w * 0.82, h * 0.18, min(w, h) * 0.045)
    _dune(cr, w, h, 0.82, 0.035, 1.1, 0.9, "#15203a")
    _dune(cr, w, h, 0.90, 0.03, 1.6, 2.6, "#0d1628")
    _dune(cr, w, h, 0.96, 0.02, 2.1, 4.1, "#080e1a")


def paint_desert(cr, w: float, h: float, t: float) -> None:
    """Sunset on the road to baghdad: the sun sinking red into the sands."""
    _vertical_gradient(cr, h, [
        (0.00, "#0b1320"), (0.28, "#2a1f3d"), (0.45, "#6e2b33"), (0.56, "#c2552c"), (0.62, "#e8893a"),
        (1.00, "#e8893a"),
    ])
    _stars(cr, w, h, t, seed=3, count=60, max_y=0.30, alpha=0.7)
    sun_r = min(w, h) * 0.11
    sx, sy = w * 0.64, h * 0.58
    _glow(cr, sx, sy, sun_r * 4.0, rgb("#ffb347"), 0.35)
    sun = cairo.RadialGradient(sx, sy - sun_r * 0.3, 0, sx, sy, sun_r)
    sun.add_color_stop_rgb(0, *rgb("#ffe08a"))
    sun.add_color_stop_rgb(1, *rgb("#e2572b"))
    cr.set_source(sun)
    cr.arc(sx, sy, sun_r, 0, math.tau)
    cr.fill()
    _dune(cr, w, h, 0.61, 0.025, 1.0, 1.2, "#8a3a26")
    _dune(cr, w, h, 0.68, 0.04, 1.3, 3.0, "#5c2620")
    # The lone figure counting by the roadside, on the middle dune
    mid = (0.68, 0.04, 1.3, 3.0)
    fx = w * 0.20
    fy = _dune_height(w, h, fx, *mid) + 2
    s = h * 0.075
    cr.set_source_rgb(*rgb("#2a1418"))
    cr.move_to(fx - s * 0.55, fy)
    cr.curve_to(fx - s * 0.5, fy - s * 0.8, fx + s * 0.4, fy - s * 0.9, fx + s * 0.5, fy)
    cr.close_path()
    cr.fill()
    cr.arc(fx, fy - s * 1.0, s * 0.22, 0, math.tau)
    cr.fill()
    near = (0.80, 0.05, 0.9, 5.0)
    _dune(cr, w, h, *near, "#2b1519")


def paint_caravan(cr, w: float, h: float, t: float) -> None:
    """Dusk on the dunes: a caravan crossing beneath a crescent moon."""
    _vertical_gradient(cr, h, [(0.0, "#070d18"), (0.35, "#13213d"), (0.58, "#3d4a6e"), (0.66, "#6b5a6e"),
                               (1.0, "#6b5a6e")])
    _stars(cr, w, h, t, seed=5, count=120, max_y=0.5)
    _crescent(cr, w * 0.18, h * 0.16, min(w, h) * 0.04)
    _dune(cr, w, h, 0.63, 0.02, 0.8, 0.3, "#2c3654")
    ridge = (0.70, 0.03, 0.7, 1.9)
    _dune(cr, w, h, *ridge, "#1a2238")
    s = h * 0.13
    silhouette = rgb("#0b0f1c")
    for i, fx in enumerate((0.40, 0.52, 0.64, 0.76)):
        x = w * fx
        y = _dune_height(w, h, x, *ridge) + s * 0.02
        _camel(cr, x, y, s * (1.0 - i * 0.05), silhouette, rider=(i in (0, 2)),
               stride=(1 if i % 2 else -1))
    # A lantern swinging from the lead rider
    lx = w * 0.76 + s * 0.55
    ly = _dune_height(w, h, w * 0.76, *ridge) - s * 0.62
    flicker = 0.75 + 0.25 * math.sin(t * 5.3) * math.sin(t * 2.1)
    _glow(cr, lx, ly, s * 0.55, rgb("#ffcf6b"), 0.45 * flicker)
    cr.set_source_rgba(*rgb("#ffe08a"), flicker)
    cr.arc(lx, ly, s * 0.045, 0, math.tau)
    cr.fill()
    _dune(cr, w, h, 0.84, 0.03, 1.4, 4.4, "#0d1322")


def paint_baghdad(cr, w: float, h: float, t: float) -> None:
    """The golden gates of baghdad rising out of the evening haze."""
    _vertical_gradient(cr, h, [(0.0, "#0b1320"), (0.30, "#241c3d"), (0.50, "#5a3d4f"), (0.60, "#a8783a"),
                               (1.0, "#a8783a")])
    _stars(cr, w, h, t, seed=9, count=90, max_y=0.38)
    _crescent(cr, w * 0.80, h * 0.13, min(w, h) * 0.035)
    city = rgb("#140e1f")
    ground = h * 0.66
    u = min(w * 0.9, h * 1.6)  # Unit size for buildings
    cx = w / 2
    cr.set_source_rgb(*city)
    # Far rooftops
    for i in range(14):
        bx = cx + (i - 7) * u * 0.075
        bh = u * (0.06 + 0.05 * ((i * 7) % 5) / 4)
        cr.rectangle(bx, ground - bh, u * 0.07, bh)
    cr.fill()
    # Domes and minarets
    for dx, r in ((-0.30, 0.055), (-0.17, 0.075), (0.18, 0.08), (0.32, 0.05)):
        _dome(cr, cx + dx * u, ground - u * 0.07, r * u)
    for mx, mh in ((-0.40, 0.30), (-0.24, 0.36), (0.25, 0.38), (0.41, 0.28)):
        _minaret(cr, cx + mx * u, ground, mh * u, u * 0.022)
    # The wall
    wall_top = ground - u * 0.10
    cr.rectangle(cx - u * 0.5, wall_top, u, ground - wall_top)
    cr.fill()
    for k in range(-25, 26):  # Crenellations
        cr.rectangle(cx + k * u * 0.02 - u * 0.006, wall_top - u * 0.012, u * 0.012, u * 0.013)
    cr.fill()
    # The gate: a tall pointed arch glowing with light from within
    gw, gh = u * 0.10, u * 0.22
    cr.rectangle(cx - gw * 1.0, ground - gh * 1.15, gw * 2.0, gh * 1.15)
    cr.fill()
    _glow(cr, cx, ground - gh * 0.4, gw * 2.4, rgb("#ffcf6b"), 0.35)
    arch = cairo.LinearGradient(0, ground - gh, 0, ground)
    arch.add_color_stop_rgb(0, *rgb("#ffe9a8"))
    arch.add_color_stop_rgb(1, *GOLD)
    cr.set_source(arch)
    cr.move_to(cx - gw * 0.55, ground)
    cr.line_to(cx - gw * 0.55, ground - gh * 0.6)
    cr.curve_to(cx - gw * 0.55, ground - gh * 0.85, cx - gw * 0.15, ground - gh * 0.95, cx, ground - gh)
    cr.curve_to(cx + gw * 0.15, ground - gh * 0.95, cx + gw * 0.55, ground - gh * 0.85, cx + gw * 0.55,
                ground - gh * 0.6)
    cr.line_to(cx + gw * 0.55, ground)
    cr.close_path()
    cr.fill()
    # Lit windows
    lights = [(cx + dx * u, ground - dy * u) for dx, dy in (
        (-0.42, 0.04), (-0.35, 0.05), (-0.28, 0.035), (-0.21, 0.05), (-0.12, 0.04), (0.12, 0.045),
        (0.2, 0.03), (0.27, 0.05), (0.36, 0.04), (0.44, 0.035), (-0.24, 0.22), (0.25, 0.24))]
    _window_lights(cr, lights, u * 0.008, t)
    # The road leading to the gate
    cr.set_source_rgb(*rgb("#3a2618"))
    cr.rectangle(0, ground, w, h - ground)
    cr.fill()
    road = cairo.LinearGradient(0, ground, 0, h)
    road.add_color_stop_rgba(0, *GOLD, 0.35)
    road.add_color_stop_rgba(1, *GOLD, 0.05)
    cr.set_source(road)
    cr.move_to(cx - gw * 0.55, ground)
    cr.line_to(cx + gw * 0.55, ground)
    cr.line_to(cx + w * 0.22, h)
    cr.line_to(cx - w * 0.22, h)
    cr.close_path()
    cr.fill()


SCENES: dict[str, Painter] = {
    "night": paint_night,
    "title": paint_title,
    "desert": paint_desert,
    "caravan": paint_caravan,
    "baghdad": paint_baghdad,
}


def scene_names() -> set[str]:
    return set(SCENES)


def paint(name: str | None, cr, w: float, h: float, t: float) -> None:
    """Paint the scene called ``name``; unknown or empty names paint a night sky."""
    SCENES.get(name or "", paint_night)(cr, w, h, t)
