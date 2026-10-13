"""The balance puzzle — the first bespoke puzzle.

Eight gold balls look identical; one is slightly heavier. Find it with the
balance scale in at most two weighings. The pure rules live in
:mod:`the_man_who_counted.game` and the scale drawing in
:mod:`.scale_view`; this page is the interactive shell around them, finishing
with a :class:`~the_man_who_counted.engine.director.PuzzleResult` for the story.

Balls can be moved by clicking (select a ball, then a pan) or by dragging them
between the staging row and the pans. The beam stays locked level until the
player weighs — otherwise simply placing balls would give the answer away.
"""

from __future__ import annotations

from gi.repository import Adw, Gdk, GObject, Gtk

from ..engine.director import PuzzleResult
from ..game import Game, GameError, Location, Tilt
from .scale_view import ScaleView, ball_content, ball_texture

_SIDES = {"left": Location.LEFT, "right": Location.RIGHT}


class BalancePuzzlePage(Adw.NavigationPage):
    """The interactive balance puzzle; emits ``finished`` with a PuzzleResult."""

    __gtype_name__ = "TmwcBalancePuzzlePage"

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }

    def __init__(self) -> None:
        # The story waits on this page, so there is no going back mid-trial.
        super().__init__(title="The Trial of the Eight Gold Balls", tag="puzzle", can_pop=False)
        self.game = Game()
        self.selected: int | None = None
        self.identify_mode = False
        self._done = False
        self._build()
        self.refresh_view("Select a ball, then place it on a pan — or drag it there.")

    # -- layout -------------------------------------------------------------
    def _build(self) -> None:
        header = Adw.HeaderBar(css_classes=["flat"])
        new_round = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="New round (N)")
        new_round.connect("clicked", lambda _b: self.action_new_game())
        header.pack_end(new_round)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                       margin_top=6, margin_bottom=18, margin_start=18, margin_end=18)

        body.append(Gtk.Label(
            label="One of the eight gold balls is slightly heavier. Find it using the balance at most twice.",
            wrap=True, justify=Gtk.Justification.CENTER, css_classes=["dim-label"],
        ))

        tallies = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        self._weighings = Gtk.Label(css_classes=["tally"])
        self._left_count = Gtk.Label(css_classes=["tally"])
        self._right_count = Gtk.Label(css_classes=["tally"])
        for label in (self._weighings, self._left_count, self._right_count):
            tallies.append(label)
        body.append(tallies)

        self._message = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER, css_classes=["puzzle-message"])
        body.append(self._message)

        self._scale = ScaleView()
        self._scale.connect("pan-activated", lambda _s, side: self._place(_SIDES[side]))
        self._scale.connect("ball-dropped", self._on_ball_dropped)
        self._scale.connect("ball-activated", lambda _s, ball: self._on_ball(ball))
        body.append(self._scale)

        body.append(Gtk.Label(label="— The eight gold balls —", css_classes=["caption", "dim-label"]))
        self._staging = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER, css_classes=["staging"])
        self._balls: list[Gtk.Button] = []
        for i in range(self.game.total_balls):
            button = Gtk.Button(label=str(i + 1), css_classes=["ball"], valign=Gtk.Align.CENTER)
            button.connect("clicked", lambda _b, ball=i: self._on_ball(ball))
            drag = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
            drag.connect("prepare", self._on_ball_drag_prepare, i)
            button.add_controller(drag)
            self._balls.append(button)
            self._staging.append(button)
        drop = Gtk.DropTarget.new(GObject.TYPE_INT, Gdk.DragAction.MOVE)
        drop.connect("drop", self._on_staging_drop)
        self._staging.add_controller(drop)
        body.append(self._staging)

        controls = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER, margin_top=6)
        self._place_left = Gtk.Button(label="◀ Left Pan", tooltip_text="Place the selected ball on the left pan (L)")
        self._place_left.connect("clicked", lambda _b: self._place(Location.LEFT))
        self._clear = Gtk.Button(label="Clear Pans", tooltip_text="Return every ball to staging (C)")
        self._clear.connect("clicked", lambda _b: self.action_clear_pans())
        self._weigh = Gtk.Button(label="Weigh", css_classes=["suggested-action"], tooltip_text="Weigh the pans (W)")
        self._weigh.connect("clicked", lambda _b: self.action_weigh())
        self._identify = Gtk.Button(css_classes=["identify"], tooltip_text="Name the heavy ball (I)")
        self._identify.connect("clicked", lambda _b: self.action_identify())
        self._place_right = Gtk.Button(label="Right Pan ▶",
                                       tooltip_text="Place the selected ball on the right pan (R)")
        self._place_right.connect("clicked", lambda _b: self._place(Location.RIGHT))
        for button in (self._place_left, self._clear, self._weigh, self._identify, self._place_right):
            button.add_css_class("pill")
            controls.append(button)
        body.append(controls)

        toolbar = Adw.ToolbarView(content=Adw.Clamp(maximum_size=900, child=body), css_classes=["puzzle"])
        toolbar.add_top_bar(header)
        self.set_child(toolbar)

        shortcuts = Gtk.ShortcutController(scope=Gtk.ShortcutScope.MANAGED)
        for key, callback in (
            ("w", self.action_weigh),
            ("l", lambda: self._place(Location.LEFT)),
            ("r", lambda: self._place(Location.RIGHT)),
            ("c", self.action_clear_pans),
            ("i", self.action_identify),
            ("n", self.action_new_game),
        ):
            shortcuts.add_shortcut(self._shortcut(key, callback))
        for i in range(self.game.total_balls):
            shortcuts.add_shortcut(self._shortcut(str(i + 1), lambda ball=i: self._on_ball(ball)))
        self.add_controller(shortcuts)

    @staticmethod
    def _shortcut(key: str, callback) -> Gtk.Shortcut:
        def run(_widget, _args) -> bool:
            callback()
            return True

        return Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(key), action=Gtk.CallbackAction.new(run))

    # -- rendering ----------------------------------------------------------
    def refresh_view(self, message: str, *, error: bool = False) -> None:
        g = self.game
        self._scale.set_pans(g.balls_in(Location.LEFT), g.balls_in(Location.RIGHT))
        self._scale.set_inviting(self.selected is not None and not self.identify_mode)

        left, right = g.pan_counts()
        self._weighings.set_label(f"Weighings  {g.weighings_taken} / {g.max_weighings}")
        self._left_count.set_label(f"Left  {left}")
        self._right_count.set_label(f"Right  {right}")
        self._message.set_label(message)
        if error:
            self._message.add_css_class("error")
        else:
            self._message.remove_css_class("error")

        for i, button in enumerate(self._balls):
            loc = g.locations[i]
            button.set_css_classes(["ball"])
            if self.identify_mode:
                button.add_css_class("guessable")
            elif self.selected == i:
                button.add_css_class("selected")
            if loc != Location.STAGING and not self.identify_mode:
                button.add_css_class("on-pan")
            button.set_tooltip_text(
                f"Ball {i + 1}" + ("" if loc == Location.STAGING else f" — on the {loc.value} pan")
            )

        self._weigh.set_sensitive(g.can_weigh() and not self.identify_mode)
        self._identify.set_sensitive(g.weighings_taken > 0 and not self._done)
        self._identify.set_label("Cancel Identify" if self.identify_mode else "Identify Heavy Ball")
        for button in (self._place_left, self._place_right, self._clear):
            button.set_sensitive(not self.identify_mode)

    # -- actions ------------------------------------------------------------
    def action_weigh(self) -> None:
        if self._done or self.identify_mode:
            return
        try:
            tilt = self.game.weigh()
        except GameError as exc:
            self.refresh_view(str(exc), error=True)
            return
        self.selected = None
        self._scale.set_tilt(tilt)
        verdict = {
            Tilt.LEFT: "The left pan sinks — it is heavier.",
            Tilt.RIGHT: "The right pan sinks — it is heavier.",
            Tilt.LEVEL: "The pans balance perfectly.",
        }[tilt]
        if self.game.weighings_left == 0:
            self._enter_identify(f"{verdict}  No weighings left — choose the heavy ball!")
        else:
            self.refresh_view(f"{verdict}  ({self.game.weighings_left} weighing left)")

    def _place(self, pan: Location) -> None:
        if self._done or self.identify_mode:
            return
        if self.selected is None:
            self.refresh_view("Select a ball from the staging row first.", error=True)
            return
        if self.game.locations[self.selected] != Location.STAGING:
            self.refresh_view("That ball is already on a pan. Click it to return it first.", error=True)
            return
        ball = self.selected
        self._move(ball, pan)
        self.selected = None
        self.refresh_view(f"Ball {ball + 1} placed on the {pan.value} pan.")

    def _move(self, ball: int, location: Location) -> None:
        """Move a ball; the beam returns to level until the next weighing."""
        self.game.place(ball, location)
        self._scale.set_tilt(None)

    def action_clear_pans(self) -> None:
        if self._done or self.identify_mode:
            return
        self.game.clear_pans()
        self._scale.set_tilt(None)
        self.selected = None
        self.refresh_view("All balls returned to the staging row.")

    def action_identify(self) -> None:
        if self._done:
            return
        if self.game.weighings_taken == 0:
            self.refresh_view("Weigh at least once before identifying.", error=True)
            return
        if self.identify_mode:
            self.identify_mode = False
            self.refresh_view("Identify cancelled. Keep playing.")
        else:
            self._enter_identify("Click the ball you believe is the heaviest.")

    def _enter_identify(self, message: str) -> None:
        self.identify_mode = True
        self.selected = None
        self.refresh_view(message)

    def action_new_game(self) -> None:
        if self._done:
            return
        self.game.new_game()
        self._scale.set_tilt(None)
        self.selected = None
        self.identify_mode = False
        self.refresh_view("New round! Select a ball, then place it on a pan.")

    # -- events -------------------------------------------------------------
    def _on_ball(self, ball: int) -> None:
        if self._done:
            return
        if self.identify_mode:
            self._make_guess(ball)
            return
        loc = self.game.locations[ball]
        if loc != Location.STAGING:
            self._move(ball, Location.STAGING)
            self.selected = None
            self.refresh_view(f"Ball {ball + 1} returned to staging.")
        elif self.selected == ball:
            self.selected = None
            self.refresh_view("Selection cleared.")
        else:
            self.selected = ball
            self.refresh_view(f"Ball {ball + 1} selected. Place it on a pan, or press it again to deselect.")

    def _on_ball_drag_prepare(self, source: Gtk.DragSource, _x: float, _y: float, ball: int):
        if self._done or self.identify_mode:
            return None
        texture = ball_texture(ball + 1)
        source.set_icon(texture, texture.get_width() // 2, texture.get_height() // 2)
        return ball_content(ball)

    def _on_ball_dropped(self, _scale, ball: int, side: str) -> None:
        if self._done or self.identify_mode:
            return
        pan = _SIDES[side]
        self._move(ball, pan)
        self.selected = None
        self.refresh_view(f"Ball {ball + 1} placed on the {pan.value} pan.")

    def _on_staging_drop(self, _target, value: int, _x: float, _y: float) -> bool:
        ball = int(value)
        if self._done or self.identify_mode or self.game.locations[ball] == Location.STAGING:
            return False
        self._move(ball, Location.STAGING)
        self.refresh_view(f"Ball {ball + 1} returned to staging.")
        return True

    def _make_guess(self, ball: int) -> None:
        won = self.game.guess(ball)
        if won:
            message = f"Ball {ball + 1} truly was the heaviest. You have the eye of a sage!"
        else:
            heavy = self.game.heavy_ball + 1
            message = f"Ball {ball + 1} was not the heaviest — it was ball {heavy}."
        self.identify_mode = False
        self._done = True
        self.refresh_view(message)
        result = PuzzleResult(won=won, detail=message)

        dialog = Adw.AlertDialog(
            heading="✦ The Sultan Is Pleased ✦" if won else "✦ The Sultan Frowns ✦",
            body=message,
        )
        dialog.add_response("continue", "Continue ▸")
        dialog.set_response_appearance("continue", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("continue")
        dialog.set_close_response("continue")
        dialog.add_css_class("won" if won else "lost")
        dialog.connect("response", lambda _d, _r: self.emit("finished", result))
        dialog.present(self)
