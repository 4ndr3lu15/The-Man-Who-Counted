---
name: play
description: Launch The Man Who Counted (GTK/libadwaita) or drive it from a script and snapshot it, to verify a change works in the real app. Use when asked to run, start, play, or screenshot the app.
---

# Play The Man Who Counted

## Launch the game

```bash
cd src && python3 -m the_man_who_counted
```

Opens the title page → "Begin the Journey" starts the prologue. Add
`GTK_DEBUG=interactive` to open the GTK Inspector alongside it (live CSS editing,
widget tree).

## Drive it and take snapshots (no clicking)

When you need to see a change without a human at the keyboard, run a script
that starts the app, steps through it from `GLib.timeout_add`, and saves window
snapshots to PNG (then read them). Write the script to the scratchpad, not the
repo. Pattern that works:

```python
import sys; sys.path.insert(0, "src")
import gi
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1"); gi.require_version("Graphene", "1.0")
from gi.repository import Gio, GLib, Graphene, Gtk
from the_man_who_counted.main import Application
from the_man_who_counted.game import Location

app = Application()
app.set_flags(app.get_flags() | Gio.ApplicationFlags.NON_UNIQUE)

def shot(path):
    win = app.get_active_window(); w, h = win.get_width(), win.get_height()
    snap = Gtk.Snapshot(); Gtk.WidgetPaintable.new(win).snapshot(snap, w, h)
    win.get_renderer().render_texture(snap.to_node(), Graphene.Rect().init(0, 0, w, h)).save_to_png(path)

def steps():                                   # Yield = milliseconds to wait
    win = app.get_active_window()
    yield 1500; shot("title.png")
    win.begin(); yield 800
    page = win.navigation.get_visible_page()   # NovelPage
    page._advance(); yield 100                 # 1st: reveal the line, 2nd: continue
    # page._choose(0)                          # When page._choices.get_visible()
    # puzzle = win.navigation.get_visible_page()
    # puzzle._on_ball(0); puzzle._place(Location.LEFT); puzzle.action_weigh()
    # win.get_visible_dialog().emit("response", "continue")   # The result dialog
    shot("story.png"); app.quit()

def on_activate(_app):
    gen = steps()
    def tick():
        try: GLib.timeout_add(next(gen), tick)
        except StopIteration: pass
        return False
    GLib.timeout_add(100, tick)

app.connect_after("activate", on_activate)
app.run([])
```

Notes:
- The window really opens on the desktop while the script runs (a few seconds).
- `_advance()` first fast-forwards the typewriter, then moves on.
- The balance puzzle needs at least one weighing before identify works;
  `puzzle.game.heavy_ball` tells you the answer for a winning run.
- To test the installed build instead, put `<prefix>/share/the-man-who-counted`
  on `sys.path`.
