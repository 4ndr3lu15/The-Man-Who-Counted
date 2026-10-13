# The Man Who Counted — project guide for Claude

A GNOME **visual novel** inspired by Malba Tahan's *O Homem que Calculava*
("The Man Who Counted"). The story is narrated; as it unfolds the player stands
in for **Beremiz Samir**, the man who counted, and solves the puzzles he faces.
Solving a puzzle advances the story.

Built with **GTK 4 + libadwaita** through **PyGObject**, installed with **Meson**,
shipped as a **Flatpak** (app ID `io.github._4ndr3lu15.TheManWhoCounted`). It is
the native remake of an earlier Textual terminal prototype (`malba.tahan`); the
story format and puzzle rules are the same.

## Rights (read before adding chapters)

*O Homem que Calculava* is still under copyright: Brazil protects it until
2044-12-31 (author died 1974, life + 70), and the English translation (Clark &
Reid, Norton 1993) has its own copyright. So:

- **Never copy text** from the book or any translation — write original prose
  that retells the scene in our own words.
- The **math puzzles themselves** (35 camels, etc.) are free to use — ideas and
  mathematical methods are not protected (Lei 9.610/98 art. 8) — but write the
  puzzle's framing fresh.
- Keep the game clearly **unofficial / fan-made**; don't use book cover art or
  publisher branding.

## Builds, not releases

The game is **pre-alpha**. There are no versioned releases (no `v1`, no semver,
no GitHub releases/tags); it is published as numbered **builds**. The build is
defined in `src/the_man_who_counted/__init__.py` (`STAGE`, `BUILD`,
`BUILD_LABEL`, shown on the title page and in About). When cutting a new build,
bump `BUILD` there **and** keep these in sync:

- `meson.build` → `version: '<stage>.<build>'` (e.g. `pre-alpha.2`);
- the metainfo `<release version="pre-alpha.N" type="development">` entry.

Stages go pre-alpha → alpha → beta; only then talk about version 1.

Roadmap: first polish the engine and the way bespoke puzzles plug into it, then
add the book one chapter at a time as YAML story scripts plus hand-crafted
puzzles. When asked to "add a chapter", that's data + a puzzle (+ maybe a painted
scene), not new engine code.

## Architecture

```
src/the_man_who_counted/
├── __init__.py       # STAGE / BUILD / BUILD_LABEL — the current build
├── main.py           # Adw.Application: app actions/accels, About, CSS, forced dark scheme
├── window.py         # MainWindow: Adw.NavigationView (title → novel → puzzle); shortcuts dialog
├── title_page.py     # TitlePage: painted sky + banner + menu; emits "begin"
├── style.css         # Palette + widget styling (overrides libadwaita CSS variables)
├── engine/           # The visual-novel engine (content-agnostic)
│   ├── anim.py       # PURE animation math (typewriter, frame cycler, easing) — unit-tested
│   ├── story.py      # PURE Scene/Beat dataclasses + YAML loader + validation — unit-tested
│   ├── director.py   # PURE generator yielding stage commands — unit-tested
│   ├── scenery.py    # Cairo painters for backgrounds, registry SCENES — tested headless
│   ├── widgets.py    # GTK: SceneryView (cross-fade), TypewriterLabel, NamePlate
│   └── novel_page.py # GTK: NovelPage, the stage that runs the director
├── puzzles/
│   ├── __init__.py   # REGISTRY: puzzle id -> (module, class), imported lazily
│   ├── balance.py    # BalancePuzzlePage — the 8-balls balance puzzle
│   └── scale_view.py # The cairo-drawn, spring-animated balance scale
├── game.py           # PURE balance-puzzle rules (no UI) — unit-tested
└── content/
    ├── characters.yaml      # The cast (name, colour per speaker)
    └── chapters/NN_*.yaml   # One scene per chapter
data/                 # .desktop, .metainfo.xml, hicolor icons (Meson installs them)
build-aux/flatpak/    # Flatpak manifest (GNOME runtime + PyYAML module)
```

Content files are read from the package directory (`importlib.resources`), so
running from `src/` and running the Meson-installed copy behave the same.

### How a chapter plays (the flow)

`TitlePage` emits `begin` → `MainWindow.begin()` loads a chapter with
`story.load_scene(...)` and pushes a `NovelPage`. When the page is first
`shown` it starts `director.play(scene)` — a generator — and pulls commands
from it: `SetArt` (performed immediately), `ShowText` / `ShowEnd` (wait for
Space/Enter/click), `AskChoice` (answer with the option's `goto` label),
`RunPuzzle` (push the puzzle page; answer with its `PuzzleResult`). Answers go
back in with `generator.send(...)`. When the generator finishes the page emits
`story-ended` and the window pops back to the title.

Because the director is a plain generator, the whole story flow is tested by
feeding it scripted answers (`tests/test_director.py`) — no GTK involved.

### The scene / beat schema (content/chapters/*.yaml)

Top level: `id`, `title`, and a list of `beats`. Each beat is a one-key mapping
naming its kind:

- `narration: "..."` — narrator voice. Optional `art: <name>`, `speed: <cps>`.
- `say: <character-id>` + `text: "..."` — dialogue. Optional `art`, `speed`.
- `choice: "prompt"` + `options: [{text, goto}]` — branch to a `label`.
- `puzzle: <id>` + optional `on_win: <label>` / `on_lose: <label>`.
- `art: <name>` (+ optional `transition: fade|cut`) — change background only.
- `label: <name>` — a jump target. `goto: <label>` — jump to one.
- `end: "closing line"` — end the scene.

`art` names refer to painters in `engine/scenery.py` `SCENES` (`desert`,
`caravan`, `baghdad`, `night`, `title`); unknown names fall back to a night sky,
and `tests/test_scenery.py` fails if a chapter uses an unpainted name.

The loader validates every `goto`/choice/branch label resolves and every
`puzzle` id is in the registry; a bad chapter raises `StoryError`, which the
window shows as a toast instead of crashing.

## Conventions

- **Standard English capitalization.** Prose, narration, dialogue, messages
  and tooltips use sentence case. Titles, buttons and menu items use title case
  (GNOME HIG header capitalization), e.g. "Begin the Journey", "Clear Pans".
  Code comments start with a capital letter.
- **Palette**: gold `#D4AF37` is the signature colour; dark navy `#0b1320`
  background, `#101c30` panels, pale gold `#F3E5AB` highlights. The app forces
  the dark scheme. Reuse these (`scenery.GOLD`, `scenery.rgb(...)`, style.css).
- **Keep animation math in `engine/anim.py`** (pure, testable); widgets apply it
  through frame-clock tick callbacks and `Adw.TimedAnimation`/`Adw.SpringAnimation`.
  Don't bury timing logic inside widgets.
- **Painters are resolution-independent** — coordinates are fractions of the
  canvas; keep the horizon around 60% height because the dialogue box covers the
  bottom ~30%.
- **Puzzles are artisanal**, not instances of a generic base. The only contract:
  a puzzle is an `Adw.NavigationPage` with a `"finished"` signal
  (`(GObject.SignalFlags.RUN_FIRST, None, (object,))`) emitted once with a
  `PuzzleResult(won=...)`. Register it in `puzzles/__init__.py` and reference its
  id from a chapter.
- **Pure logic stays UI-free** (`game.py`, `engine/story.py`, `engine/anim.py`,
  `engine/director.py`) so it can be unit-tested without a display. The puzzle
  registry is lazy so importing it never pulls in GTK.
- GObject subclasses get a `__gtype_name__` prefixed `Tmwc`.

## Running & testing

```bash
cd src && python3 -m the_man_who_counted        # Play it from the tree
python3 -m pytest                               # Unit tests (from the repo root)
meson setup _build && meson test -C _build      # Validate desktop + metainfo
flatpak-builder --user --install --force-clean _flatpak build-aux/flatpak/*.json
```

System dependencies (Arch): `python-gobject libadwaita python-yaml python-pytest`.

For verifying UI changes without clicking around, drive the app from a script:
start `Application`, then from `GLib.timeout_add` steps call
`window.begin()`, `novel_page._advance()`, `novel_page._choose(i)`, and the
puzzle page's `_on_ball(i)` / `_place(Location.LEFT)` / `action_weigh()`; take
snapshots with `Gtk.WidgetPaintable` → `Gtk.Snapshot` → `renderer.render_texture`
→ `texture.save_to_png`. The `/play` skill has a template.

## Skills

- `/play` — Launch the app (or drive it and snapshot it) to verify a change.
- `/new-chapter` — Scaffold a new `content/chapters/NN_*.yaml`.
- `/new-puzzle` — Scaffold a new bespoke puzzle page + registry entry.
