"""Animated GTK widgets that make the stage feel alive.

Each widget keeps its *timing math* in :mod:`the_man_who_counted.engine.anim`
and only applies the results here — to frame-clock tick callbacks and
``Adw.TimedAnimation`` values. That split is what lets the engine's behaviour be
unit-tested without a display.
"""

from __future__ import annotations

from gi.repository import Adw, GLib, Gtk

from . import anim, scenery

# Ambient motion (twinkling stars, lanterns) only needs a gentle frame rate.
_AMBIENT_FPS = 20.0


def _animations_enabled() -> bool:
    settings = Gtk.Settings.get_default()
    return settings is None or settings.props.gtk_enable_animations


class SceneryView(Gtk.DrawingArea):
    """A painted background that cross-fades when its scene changes."""

    __gtype_name__ = "TmwcSceneryView"

    def __init__(self, scene: str | None = None) -> None:
        super().__init__(hexpand=True, vexpand=True)
        self._current = scene
        self._previous: str | None = None
        self._mix = 1.0
        self._time = 0.0
        self._last_frame = 0.0
        self.set_draw_func(self._draw)
        self._fade = Adw.TimedAnimation.new(
            self, 0.0, 1.0, 600, Adw.CallbackAnimationTarget.new(self._on_mix)
        )
        self._fade.connect("done", self._on_fade_done)
        self.add_tick_callback(self._on_tick)

    @property
    def scene(self) -> str | None:
        return self._current

    def show(self, scene: str | None, *, transition: str = "fade") -> None:
        if scene == self._current:
            return
        if transition == "fade" and self.get_mapped():
            self._previous = self._current
            self._current = scene
            self._fade.reset()
            self._fade.play()
        else:
            self._previous = None
            self._current = scene
            self._mix = 1.0
            self.queue_draw()

    def _on_mix(self, value: float) -> None:
        self._mix = value
        self.queue_draw()

    def _on_fade_done(self, _animation) -> None:
        self._previous = None
        self._mix = 1.0
        self.queue_draw()

    def _on_tick(self, _widget, clock) -> bool:
        if not _animations_enabled():
            return GLib.SOURCE_CONTINUE
        now = clock.get_frame_time() / 1_000_000
        self._time = now
        if now - self._last_frame >= 1.0 / _AMBIENT_FPS:
            self._last_frame = now
            self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _draw(self, _area, cr, width: int, height: int) -> None:
        if self._previous is not None and self._mix < 1.0:
            scenery.paint(self._previous, cr, width, height, self._time)
            cr.push_group()
            scenery.paint(self._current, cr, width, height, self._time)
            cr.pop_group_to_source()
            cr.paint_with_alpha(anim.ease_in_out(self._mix))
        else:
            scenery.paint(self._current, cr, width, height, self._time)


class NamePlate(Gtk.Label):
    """Shows the current speaker's name, popping in when the speaker changes."""

    __gtype_name__ = "TmwcNamePlate"

    def __init__(self) -> None:
        super().__init__(xalign=0.0, css_classes=["nameplate"])
        self._current: str | None = None
        self._pop = Adw.TimedAnimation.new(
            self, 0.0, 1.0, 250, Adw.PropertyAnimationTarget.new(self, "opacity")
        )

    def set_speaker(self, name: str, color: str) -> None:
        if name == self._current:
            return
        self._current = name
        self.set_markup(f'<span foreground="{color}">{GLib.markup_escape_text(name)}</span>')
        # A small pop: appear from transparent so the eye catches the new speaker.
        self._pop.play()

    def clear_speaker(self) -> None:
        self._current = None
        self._pop.skip()
        self.set_text(" ")


class TypewriterLabel(Gtk.Label):
    """Reveals text one character at a time, then waits to be advanced.

    The not-yet-revealed tail is laid out but drawn fully transparent, so words
    never jump between lines as the text grows. Press-to-skip is handled by the
    page: while :attr:`is_revealing` is true a press calls :meth:`fast_forward`;
    once revealed, a press advances the beat.
    """

    __gtype_name__ = "TmwcTypewriterLabel"

    def __init__(self) -> None:
        super().__init__(
            xalign=0.0, yalign=0.0, wrap=True, valign=Gtk.Align.START, css_classes=["dialogue-line"]
        )
        self._full = ""
        self._cps = anim.DEFAULT_CPS
        self._start: float | None = None
        self._tick_id: int | None = None
        self._shown = -1

    @property
    def is_revealing(self) -> bool:
        return self._tick_id is not None

    def reveal(self, text: str, *, cps: float | None = None) -> None:
        self._stop()
        self._full = text
        self._cps = cps if cps is not None else anim.DEFAULT_CPS
        self._start = None
        self._shown = -1
        if anim.is_typewriter_done(0.0, len(text), self._cps):
            self._finish()
        else:
            self._render(0)
            self._tick_id = self.add_tick_callback(self._tick)

    def fast_forward(self) -> None:
        if self.is_revealing:
            self._finish()

    def _tick(self, _widget, clock) -> bool:
        now = clock.get_frame_time() / 1_000_000
        if self._start is None:
            self._start = now
        elapsed = now - self._start
        self._render(anim.typewriter_index(elapsed, len(self._full), self._cps))
        if anim.is_typewriter_done(elapsed, len(self._full), self._cps):
            self._tick_id = None
            self._finish()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _render(self, n: int) -> None:
        if n == self._shown:
            return
        self._shown = n
        shown = GLib.markup_escape_text(self._full[:n])
        hidden = GLib.markup_escape_text(self._full[n:])
        self.set_markup(f'{shown}<span alpha="1">{hidden}</span>' if hidden else shown)

    def _finish(self) -> None:
        self._stop()
        self._render(len(self._full))

    def _stop(self) -> None:
        if self._tick_id is not None:
            self.remove_tick_callback(self._tick_id)
            self._tick_id = None
