"""The title page: drifting desert stars behind a gold banner."""

from __future__ import annotations

from gi.repository import Adw, GObject, Gtk

from . import BUILD_LABEL
from .engine.widgets import SceneryView

MENU_XML = """
<interface>
  <menu id="primary">
    <section>
      <item><attribute name="label">Keyboard Shortcuts</attribute><attribute name="action">app.shortcuts</attribute></item>
      <item><attribute name="label">About The Man Who Counted</attribute><attribute name="action">app.about</attribute></item>
    </section>
  </menu>
</interface>
"""


class TitlePage(Adw.NavigationPage):
    __gtype_name__ = "TmwcTitlePage"

    __gsignals__ = {
        "begin": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self) -> None:
        super().__init__(title="The Man Who Counted", tag="title")

        menu = Gtk.Builder.new_from_string(MENU_XML, -1).get_object("primary")
        header = Adw.HeaderBar(css_classes=["flat"], show_title=False)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu,
                                       primary=True, tooltip_text="Main Menu"))

        self._menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                             halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, margin_start=24, margin_end=24)
        self._menu.append(Gtk.Label(label="THE MAN WHO COUNTED", wrap=True,
                                    justify=Gtk.Justification.CENTER, css_classes=["title-banner"]))
        self._menu.append(Gtk.Label(label="·  O Homem que Calculava  ·", css_classes=["title-sub"]))
        self._menu.append(Gtk.Label(label="A visual novel inspired by Malba Tahan",
                                    css_classes=["tagline"], margin_bottom=28))

        begin = Gtk.Button(label="Begin the Journey", css_classes=["pill", "suggested-action", "menu-button"])
        begin.connect("clicked", lambda _b: self.emit("begin"))
        later = Gtk.Button(label="Continue (Coming Soon)", sensitive=False, css_classes=["pill", "menu-button"])
        quit_ = Gtk.Button(label="Quit", action_name="app.quit", css_classes=["pill", "menu-button"])
        for button in (begin, later, quit_):
            button.set_halign(Gtk.Align.CENTER)
            self._menu.append(button)
        self._begin = begin
        self._menu.append(Gtk.Label(label=BUILD_LABEL, css_classes=["caption", "build-label"], margin_top=18))

        overlay = Gtk.Overlay(child=SceneryView("title"))
        overlay.add_overlay(self._menu)
        toolbar = Adw.ToolbarView(content=overlay, extend_content_to_top_edge=True)
        toolbar.add_top_bar(header)
        self.set_child(toolbar)

        # Gentle fade-in so the title arrives rather than just appearing.
        self._menu.set_opacity(0.0)
        self._fade = Adw.TimedAnimation.new(
            self._menu, 0.0, 1.0, 1200, Adw.PropertyAnimationTarget.new(self._menu, "opacity")
        )
        self.connect("shown", self._on_shown)

    def _on_shown(self, _page) -> None:
        if self._menu.get_opacity() < 1.0:
            self._fade.play()
        self._begin.grab_focus()
