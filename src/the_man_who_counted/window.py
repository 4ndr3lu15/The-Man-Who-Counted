"""The main window: a navigation stack of title → story → puzzle pages."""

from __future__ import annotations

from gi.repository import Adw

from .engine.novel_page import NovelPage
from .engine.story import StoryError, load_scene
from .puzzles import make_puzzle, puzzle_ids
from .title_page import TitlePage

OPENING_CHAPTER = "00_prologue"


class MainWindow(Adw.ApplicationWindow):
    __gtype_name__ = "TmwcMainWindow"

    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title="The Man Who Counted",
                         default_width=1100, default_height=760, width_request=560, height_request=620)
        self._nav = Adw.NavigationView()
        title = TitlePage()
        title.connect("begin", lambda _p: self.begin())
        self._nav.add(title)
        self._toasts = Adw.ToastOverlay(child=self._nav)
        self.set_content(self._toasts)

    @property
    def navigation(self) -> Adw.NavigationView:
        return self._nav

    def begin(self, chapter: str = OPENING_CHAPTER) -> None:
        try:
            scene = load_scene(chapter, known_puzzles=puzzle_ids())
        except StoryError as exc:  # Surface a malformed chapter instead of crashing
            self._toasts.add_toast(Adw.Toast(title=f"Could not load chapter: {exc}", timeout=8))
            return
        page = NovelPage(scene, make_puzzle)
        page.connect("story-ended", lambda _p: self._nav.pop_to_tag("title"))
        self._nav.push(page)


def shortcuts_dialog() -> Adw.ShortcutsDialog:
    dialog = Adw.ShortcutsDialog()
    sections = {
        "Story": [
            ("Continue / reveal the whole line", "space"),
            ("Continue", "Return"),
            ("Pick a choice", "1"),
        ],
        "The Trial of the Eight Gold Balls": [
            ("Select a ball", "1"),
            ("Place on the left pan", "l"),
            ("Place on the right pan", "r"),
            ("Weigh", "w"),
            ("Clear the pans", "c"),
            ("Identify the heavy ball", "i"),
            ("New round", "n"),
        ],
        "General": [
            ("Keyboard shortcuts", "<Control>question"),
            ("Quit", "<Control>q"),
        ],
    }
    for title, items in sections.items():
        section = Adw.ShortcutsSection(title=title)
        for label, accel in items:
            section.add(Adw.ShortcutsItem(title=label, accelerator=accel))
        dialog.add(section)
    return dialog
