"""The application: an ``Adw.Application`` that opens the main window."""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from . import BUILD_LABEL  # noqa: E402

APP_ID = "io.github._4ndr3lu15.TheManWhoCounted"
STYLE = Path(__file__).with_name("style.css")


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._add_action("quit", lambda *_: self.quit(), ["<Control>q"])
        self._add_action("about", self._on_about)
        self._add_action("shortcuts", self._on_shortcuts, ["<Control>question"])

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        # The desert night is the game's palette; it is always dark.
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(STYLE))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        # Running from a source checkout: find the app icon in data/icons.
        dev_icons = Path(__file__).resolve().parents[2] / "data" / "icons"
        if dev_icons.is_dir():
            Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(str(dev_icons))

    def do_activate(self) -> None:
        from .window import MainWindow

        window = self.get_active_window() or MainWindow(self)
        window.present()

    def _add_action(self, name: str, callback, accels: list[str] | None = None) -> None:
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if accels:
            self.set_accels_for_action(f"app.{name}", accels)

    def _on_about(self, *_args) -> None:
        about = Adw.AboutDialog(
            application_name="The Man Who Counted",
            application_icon=APP_ID,
            developer_name="André Luís",
            version=BUILD_LABEL,
            comments="A visual novel inspired by Malba Tahan's “The Man Who Counted” "
                     "(O Homem que Calculava). You stand in the sandals of Beremiz Samir — "
                     "when he meets a riddle, so do you.",
            website="https://github.com/4ndr3lu15/The-Man-Who-Counted",
            issue_url="https://github.com/4ndr3lu15/The-Man-Who-Counted/issues",
            developers=["André Luís"],
            copyright="© 2026 André Luís",
            license_type=Gtk.License.MIT_X11,
        )
        about.present(self.get_active_window())

    def _on_shortcuts(self, *_args) -> None:
        from .window import shortcuts_dialog

        shortcuts_dialog().present(self.get_active_window())


def main(argv: list[str] | None = None) -> int:
    return Application().run(sys.argv if argv is None else argv)
