"""The balance scale, drawn with cairo.

Replaces the terminal version's character-grid ``scale_art``. The beam swings on
a spring (so a weighing wobbles before it settles), the pans hang level from
their chains, and the balls sitting in each pan are drawn as numbered gold
spheres. The view is clickable — a pan to drop the selected ball into it, a ball
to send it back — and accepts balls dragged onto either pan.
"""

from __future__ import annotations

import math

import cairo
from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from ..engine.scenery import GOLD, PALE_GOLD, rgb
from ..game import Location, Tilt

# How far the beam tips for a weighing, in radians.
TILT_ANGLE = 0.16


def draw_ball(cr, x: float, y: float, r: float, number: int, *, highlight: bool = False) -> None:
    """A gold sphere with its number engraved on it."""
    cr.save()
    cr.set_source_rgba(0, 0, 0, 0.35)
    cr.arc(x + r * 0.12, y + r * 0.18, r, 0, math.tau)
    cr.fill()
    grad = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
    grad.add_color_stop_rgb(0.0, *rgb("#fff3c4"))
    grad.add_color_stop_rgb(0.45, *GOLD)
    grad.add_color_stop_rgb(1.0, *rgb("#7a5c12"))
    cr.set_source(grad)
    cr.arc(x, y, r, 0, math.tau)
    cr.fill()
    if highlight:
        cr.set_source_rgba(*PALE_GOLD, 0.9)
        cr.set_line_width(max(2.0, r * 0.12))
        cr.arc(x, y, r + 2, 0, math.tau)
        cr.stroke()
    cr.set_source_rgb(*rgb("#3a2a05"))
    cr.select_font_face("serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(r * 0.95)
    label = str(number)
    ext = cr.text_extents(label)
    cr.move_to(x - ext.width / 2 - ext.x_bearing, y - ext.height / 2 - ext.y_bearing)
    cr.show_text(label)
    cr.restore()


def ball_texture(number: int, r: float = 20.0) -> Gdk.Texture:
    """A ball rendered to a texture — used as the icon while dragging it."""
    size = int(r * 2 + 8)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw_ball(cairo.Context(surface), size / 2 - 1, size / 2 - 1, r, number)
    surface.flush()
    return Gdk.MemoryTexture.new(
        size, size, Gdk.MemoryFormat.B8G8R8A8_PREMULTIPLIED,
        GLib.Bytes.new(bytes(surface.get_data())), surface.get_stride(),
    )


def ball_content(ball: int) -> Gdk.ContentProvider:
    """Drag payload for a (0-based) ball."""
    return Gdk.ContentProvider.new_for_value(GObject.Value(GObject.TYPE_INT, ball))


class ScaleView(Gtk.DrawingArea):
    """The interactive balance scale."""

    __gtype_name__ = "TmwcScaleView"

    __gsignals__ = {
        # "left" or "right": the player clicked (or dropped onto) a pan.
        "pan-activated": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        # A ball (0-based) dropped onto a pan: (ball, "left"/"right").
        "ball-dropped": (GObject.SignalFlags.RUN_FIRST, None, (int, str)),
        # A ball (0-based) sitting in a pan was clicked.
        "ball-activated": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self) -> None:
        super().__init__(hexpand=True, vexpand=True, content_height=260, content_width=420)
        self._left: list[int] = []
        self._right: list[int] = []
        self._angle = 0.0
        self._inviting = False  # A ball is selected: pans glow as drop targets
        self._hover_pan: str | None = None
        self._pan_boxes: dict[str, tuple[float, float, float, float]] = {}
        self._ball_spots: list[tuple[int, float, float, float]] = []

        self.set_draw_func(self._draw)
        self._spring = Adw.SpringAnimation.new(
            self, 0.0, 0.0, Adw.SpringParams.new(0.22, 1.0, 140.0),
            Adw.CallbackAnimationTarget.new(self._set_angle),
        )

        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        self.add_controller(click)

        drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        drag.connect("prepare", self._on_drag_prepare)
        self.add_controller(drag)

        drop = Gtk.DropTarget.new(GObject.TYPE_INT, Gdk.DragAction.MOVE)
        drop.connect("motion", self._on_drop_motion)
        drop.connect("leave", self._on_drop_leave)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

    # -- state ----------------------------------------------------------------
    def set_pans(self, left: list[int], right: list[int]) -> None:
        self._left, self._right = sorted(left), sorted(right)
        self.queue_draw()

    def set_inviting(self, inviting: bool) -> None:
        self._inviting = inviting
        self.queue_draw()

    def set_tilt(self, tilt: Tilt | None) -> None:
        """Swing the beam to show ``tilt`` (``None`` = level and locked)."""
        target = 0.0 if tilt is None else tilt.value * TILT_ANGLE
        self._spring.set_value_from(self._angle)
        self._spring.set_value_to(target)
        self._spring.play()

    def _set_angle(self, value: float) -> None:
        self._angle = value
        self.queue_draw()

    # -- hit testing ------------------------------------------------------------
    def ball_at(self, x: float, y: float) -> int | None:
        for ball, bx, by, r in self._ball_spots:
            if (x - bx) ** 2 + (y - by) ** 2 <= r * r:
                return ball
        return None

    def pan_at(self, x: float, y: float) -> str | None:
        for side, (px, py, pw, ph) in self._pan_boxes.items():
            if px <= x <= px + pw and py <= y <= py + ph:
                return side
        # Generous fallback: anything on that half of the scale, below the beam.
        width = self.get_width()
        if width and y > self.get_height() * 0.2:
            return Location.LEFT.value if x < width / 2 else Location.RIGHT.value
        return None

    def _on_click(self, _gesture, _n: int, x: float, y: float) -> None:
        ball = self.ball_at(x, y)
        if ball is not None:
            self.emit("ball-activated", ball)
            return
        side = self.pan_at(x, y)
        if side is not None:
            self.emit("pan-activated", side)

    def _on_drag_prepare(self, source: Gtk.DragSource, x: float, y: float):
        ball = self.ball_at(x, y)
        if ball is None:
            return None
        texture = ball_texture(ball + 1)
        source.set_icon(texture, texture.get_width() // 2, texture.get_height() // 2)
        return ball_content(ball)

    def _on_drop_motion(self, _target, x: float, y: float) -> Gdk.DragAction:
        side = self.pan_at(x, y)
        if side != self._hover_pan:
            self._hover_pan = side
            self.queue_draw()
        return Gdk.DragAction.MOVE if side else Gdk.DragAction(0)

    def _on_drop_leave(self, _target) -> None:
        self._hover_pan = None
        self.queue_draw()

    def _on_drop(self, _target, value: int, x: float, y: float) -> bool:
        self._hover_pan = None
        side = self.pan_at(x, y)
        if side is None:
            return False
        self.emit("ball-dropped", int(value), side)
        return True

    # -- drawing ----------------------------------------------------------------
    def _draw(self, _area, cr, width: int, height: int) -> None:
        cx = width / 2
        pivot_y = height * 0.14
        arm = min(width * 0.34, height * 0.75, 300)
        chain = height * 0.34
        pan_half = arm * 0.46
        ball_r = max(9.0, min(pan_half / 4.4, 20.0))
        base_y = height * 0.94

        gold_stroke = cairo.LinearGradient(0, pivot_y, 0, base_y)
        gold_stroke.add_color_stop_rgb(0, *rgb("#f3dc8a"))
        gold_stroke.add_color_stop_rgb(1, *rgb("#8a6d1a"))

        # Stand
        cr.set_source(gold_stroke)
        cr.set_line_width(7)
        cr.move_to(cx, pivot_y)
        cr.line_to(cx, base_y - 14)
        cr.stroke()
        cr.move_to(cx - arm * 0.36, base_y)
        cr.line_to(cx - arm * 0.16, base_y - 16)
        cr.line_to(cx + arm * 0.16, base_y - 16)
        cr.line_to(cx + arm * 0.36, base_y)
        cr.close_path()
        cr.fill()

        # Beam
        cos_a, sin_a = math.cos(self._angle), math.sin(self._angle)
        ends = {
            "left": (cx - arm * cos_a, pivot_y - arm * sin_a),
            "right": (cx + arm * cos_a, pivot_y + arm * sin_a),
        }
        cr.set_source(gold_stroke)
        cr.set_line_width(6)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(*ends["left"])
        cr.line_to(*ends["right"])
        cr.stroke()
        for ex, ey in ends.values():
            cr.arc(ex, ey, 5, 0, math.tau)
            cr.fill()
        # Finial
        cr.set_source_rgb(*PALE_GOLD)
        cr.move_to(cx, pivot_y - 26)
        cr.line_to(cx + 9, pivot_y - 8)
        cr.line_to(cx, pivot_y + 4)
        cr.line_to(cx - 9, pivot_y - 8)
        cr.close_path()
        cr.fill()
        cr.set_source(gold_stroke)
        cr.arc(cx, pivot_y, 8, 0, math.tau)
        cr.fill()

        # Pans
        self._pan_boxes = {}
        self._ball_spots = []
        for side, balls in (("left", self._left), ("right", self._right)):
            ex, ey = ends[side]
            rim_y = ey + chain
            self._draw_pan(cr, side, ex, ey, rim_y, pan_half, gold_stroke)
            self._draw_pan_balls(cr, balls, ex, rim_y, pan_half, ball_r)
            top = rim_y - ball_r * 2 * 3
            self._pan_boxes[side] = (ex - pan_half - 8, top, pan_half * 2 + 16, rim_y + pan_half * 0.4 - top + 8)

    def _draw_pan(self, cr, side: str, ex: float, ey: float, rim_y: float, half: float, stroke) -> None:
        glow = self._hover_pan == side or (self._inviting and self._hover_pan is None)
        if glow:
            strength = 0.35 if self._hover_pan == side else 0.14
            grad = cairo.RadialGradient(ex, rim_y, 0, ex, rim_y, half * 1.6)
            grad.add_color_stop_rgba(0, *GOLD, strength)
            grad.add_color_stop_rgba(1, *GOLD, 0)
            cr.set_source(grad)
            cr.arc(ex, rim_y, half * 1.6, 0, math.tau)
            cr.fill()
        # Chains
        cr.set_source_rgba(*PALE_GOLD, 0.75)
        cr.set_line_width(1.5)
        for dx in (-half * 0.92, 0, half * 0.92):
            cr.move_to(ex, ey)
            cr.line_to(ex + dx, rim_y)
        cr.stroke()
        # Bowl
        cr.set_source(stroke)
        cr.move_to(ex - half, rim_y)
        cr.curve_to(ex - half * 0.8, rim_y + half * 0.42, ex + half * 0.8, rim_y + half * 0.42, ex + half, rim_y)
        cr.close_path()
        cr.fill()
        cr.set_source_rgb(*rgb("#f3dc8a"))
        cr.set_line_width(2)
        cr.move_to(ex - half - 3, rim_y)
        cr.line_to(ex + half + 3, rim_y)
        cr.stroke()

    def _draw_pan_balls(self, cr, balls: list[int], ex: float, rim_y: float, half: float, r: float) -> None:
        per_row = max(1, int((half * 2) // (r * 2.1)))
        for i, ball in enumerate(balls):
            row, col = divmod(i, per_row)
            in_row = min(per_row, len(balls) - row * per_row)
            x = ex + (col - (in_row - 1) / 2) * r * 2.1
            y = rim_y - r - row * r * 1.8
            draw_ball(cr, x, y, r, ball + 1)
            self._ball_spots.append((ball, x, y, r))
