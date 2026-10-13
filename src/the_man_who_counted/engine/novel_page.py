"""The visual-novel stage: a painted background under a dialogue box.

This is the *view* the director talks to. It pulls commands from the
:func:`~the_man_who_counted.engine.director.play` generator one at a time,
performs each (reveal a line, offer a choice, push a puzzle page...) and sends
the player's answer back once they act. It also handles the press-to-skip /
press-to-advance dance so the director can stay declarative.
"""

from __future__ import annotations

from typing import Callable

from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from . import director
from .director import AskChoice, PuzzleResult, RunPuzzle, SetArt, ShowEnd, ShowText
from .story import ChoiceOption, Scene
from .widgets import NamePlate, SceneryView, TypewriterLabel

# Puzzle id -> a fresh puzzle page that emits "finished" with a PuzzleResult.
PuzzleFactory = Callable[[str], Adw.NavigationPage]

_ADVANCE_KEYS = {Gdk.KEY_space, Gdk.KEY_Return, Gdk.KEY_KP_Enter}
_CONTINUE_HINT = "Press Space or click to continue"


class NovelPage(Adw.NavigationPage):
    """Plays one :class:`~the_man_who_counted.engine.story.Scene` to completion."""

    __gtype_name__ = "TmwcNovelPage"

    __gsignals__ = {
        # Emitted once the closing line has been dismissed.
        "story-ended": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, scene: Scene, puzzle_factory: PuzzleFactory) -> None:
        super().__init__(title=scene.title, tag="novel")
        self.scene = scene
        self._puzzle_factory = puzzle_factory
        self._flow = director.play(scene)
        self._started = False
        self._waiting = False  # A line is fully shown and waits for the player
        self._choice_options: list[ChoiceOption] = []

        self._scenery = SceneryView()
        self._nameplate = NamePlate()
        self._line = TypewriterLabel()
        self._hint = Gtk.Label(label=_CONTINUE_HINT, xalign=1.0, css_classes=["hint"])
        self._choices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, visible=False)

        dialogue = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["dialogue"], height_request=190
        )
        dialogue.append(self._nameplate)
        dialogue.append(self._line)
        dialogue.append(Gtk.Box(vexpand=True))
        dialogue.append(self._choices)
        dialogue.append(self._hint)

        clamp = Adw.Clamp(
            maximum_size=980, child=dialogue, valign=Gtk.Align.END,
            margin_start=18, margin_end=18, margin_bottom=18,
        )
        overlay = Gtk.Overlay(child=self._scenery)
        overlay.add_overlay(clamp)

        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        overlay.add_controller(click)

        header = Adw.HeaderBar(css_classes=["flat"])
        toolbar = Adw.ToolbarView(content=overlay, extend_content_to_top_edge=True)
        toolbar.add_top_bar(header)
        self.set_child(toolbar)

        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        self.connect("shown", self._on_shown)

    # -- driving the director -----------------------------------------------
    def _on_shown(self, _page) -> None:
        # "shown" fires again when we come back from a puzzle; start only once.
        if not self._started:
            self._started = True
            self._step(None)

    def _step(self, answer) -> None:
        """Send ``answer`` to the director and perform commands until one needs the player."""
        while True:
            try:
                command = self._flow.send(answer)
            except StopIteration:
                self.emit("story-ended")
                return
            answer = None
            if isinstance(command, SetArt):
                self._scenery.show(command.art, transition=command.transition)
                continue
            if isinstance(command, ShowText):
                self._show_text(command)
            elif isinstance(command, AskChoice):
                self._ask_choice(command)
            elif isinstance(command, RunPuzzle):
                self._run_puzzle(command.puzzle_id)
            elif isinstance(command, ShowEnd):
                self._show_end(command.text)
            return

    # -- the vocabulary -----------------------------------------------------
    def _show_text(self, command: ShowText) -> None:
        self._choices.set_visible(False)
        if command.name is None:
            self._nameplate.clear_speaker()
        else:
            self._nameplate.set_speaker(command.name, command.color)
        self._hint.set_label(_CONTINUE_HINT)
        self._hint.set_visible(True)
        self._line.reveal(command.text, cps=command.speed)
        self._waiting = True

    def _show_end(self, text: str | None) -> None:
        self._nameplate.clear_speaker()
        self._hint.set_label("Press Space to leave")
        self._hint.set_visible(True)
        self._line.reveal(text or "— End of the prologue —")
        self._waiting = True

    def _ask_choice(self, command: AskChoice) -> None:
        self._nameplate.clear_speaker()
        self._line.reveal(command.prompt, cps=0)  # Show the prompt instantly
        self._hint.set_visible(False)
        self._choice_options = list(command.options)
        while (child := self._choices.get_first_child()) is not None:
            self._choices.remove(child)
        for idx, opt in enumerate(self._choice_options):
            label = Gtk.Label(label=f"{idx + 1}.  {opt.text}", xalign=0.0, wrap=True)
            button = Gtk.Button(child=label, css_classes=["choice"])
            button.connect("clicked", lambda _b, i=idx: self._choose(i))
            self._choices.append(button)
        self._choices.set_visible(True)
        first = self._choices.get_first_child()
        if first is not None:
            first.grab_focus()

    def _choose(self, idx: int) -> None:
        if not self._choices.get_visible() or not 0 <= idx < len(self._choice_options):
            return
        goto = self._choice_options[idx].goto
        self._choices.set_visible(False)
        self._choice_options = []
        self._step(goto)

    def _run_puzzle(self, puzzle_id: str) -> None:
        page = self._puzzle_factory(puzzle_id)
        page.connect("finished", self._on_puzzle_finished)
        self._navigation_view().push(page)

    def _on_puzzle_finished(self, _page, result: PuzzleResult) -> None:
        self._navigation_view().pop_to_page(self)

        def resume() -> bool:
            self._step(result)
            return GLib.SOURCE_REMOVE

        GLib.idle_add(resume)

    def _navigation_view(self) -> Adw.NavigationView:
        return self.get_ancestor(Adw.NavigationView)

    # -- input --------------------------------------------------------------
    def _advance(self) -> None:
        if self._choices.get_visible():
            return
        if self._line.is_revealing:
            self._line.fast_forward()
        elif self._waiting:
            self._waiting = False
            self._step(None)

    def _on_click(self, _gesture, _n_press: int, _x: float, _y: float) -> None:
        self._advance()

    def _on_key(self, _controller, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        if self._choices.get_visible():
            # Number keys pick a choice; space/enter activate the focused one.
            char = chr(Gdk.keyval_to_unicode(keyval) or 0)
            if char.isdigit() and char != "0":
                self._choose(int(char) - 1)
                return True
            return False
        if keyval in _ADVANCE_KEYS:
            self._advance()
            return True
        return False
