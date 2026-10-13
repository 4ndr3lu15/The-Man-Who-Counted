# The Man Who Counted

A **visual novel** for the GNOME desktop, inspired by the Brazilian book **“The
Man Who Counted”** (*O Homem que Calculava*) by **Malba Tahan**.

The story is narrated, and as it unfolds you stand in the sandals of **Beremiz
Samir**, the man who counted. When Beremiz meets a riddle, so do you — and
solving the puzzle carries the story forward.

Written in **Python** with **GTK 4** and **libadwaita** (PyGObject), built with
**Meson** and packaged with **Flatpak**.

> An unofficial, fan-made game. It is not affiliated with or endorsed by Malba
> Tahan's estate or any publisher of the book. The story text in this repository
> is original writing inspired by the book, not taken from it.

---

## Status: pre-alpha

This is **pre-alpha** software — not a release. There are no versions yet; the
game is published as numbered **builds**. The current one is **pre-alpha build
1**, which contains:

- An animated title page and a narrated **prologue** — meeting Beremiz on the
  road to Baghdad.
- Hand-painted (cairo) backgrounds that cross-fade, with twinkling stars and
  flickering lanterns; a typewriter dialogue box; branching choices.
- The first bespoke puzzle, the **Trial of the Eight Gold Balls**: find the one
  heavier ball with a balance, in two weighings. The scale is spring-animated,
  the balls can be clicked or dragged onto the pans, and the outcome changes
  what Beremiz says next.

Next: polish the engine and the way puzzles plug into it, then add the book's
episodes one chapter at a time.

---

## Running it

### From the source tree (quickest)

Needs GTK 4, libadwaita ≥ 1.8, PyGObject and PyYAML from your distribution
(Arch: `pacman -S python-gobject libadwaita python-yaml`; Fedora:
`dnf install python3-gobject libadwaita python3-pyyaml`).

```bash
cd src && python3 -m the_man_who_counted
```

### Installed with Meson

```bash
meson setup _build --prefix="$HOME/.local"
meson install -C _build
the-man-who-counted
```

### As a Flatpak build

```bash
flatpak-builder --user --install --force-clean _flatpak \
    build-aux/flatpak/io.github._4ndr3lu15.TheManWhoCounted.json
flatpak run io.github._4ndr3lu15.TheManWhoCounted
```

### Controls

Advance dialogue with **Space** / **Enter** or a click (once to reveal the whole
line, again to continue); pick choices with the number keys or by clicking. In
the balance trial: **1–8** select a ball, **L** / **R** place it, **W** weigh,
**C** clear, **I** identify, **N** new round — or just drag the balls around.
**Ctrl+?** shows every shortcut.

---

## Project layout

```
src/the_man_who_counted/
├── __init__.py       # Build stage and number (pre-alpha, build N)
├── main.py           # Adw.Application: actions, About, CSS, dark palette
├── window.py         # The window: title → story → puzzle navigation stack
├── title_page.py     # The animated title page
├── style.css         # The gold-on-navy palette
├── engine/           # The visual-novel engine (content-agnostic)
│   ├── anim.py       # Pure animation math (typewriter, easing) — unit-tested
│   ├── story.py      # Scene/beat model + YAML loader + validation — unit-tested
│   ├── director.py   # Pure generator: walks the beats, yields stage commands — unit-tested
│   ├── scenery.py    # The painted backgrounds (cairo painters)
│   ├── widgets.py    # SceneryView, TypewriterLabel, NamePlate
│   └── novel_page.py # The stage (background + dialogue box) that runs the director
├── puzzles/          # Bespoke, hand-crafted puzzle pages (balance, ...)
├── game.py           # Pure balance-puzzle rules (no UI) — unit-tested
└── content/          # The story as data: characters.yaml + chapters/*.yaml
data/                 # Desktop file, AppStream metainfo, icons
build-aux/flatpak/    # Flatpak manifest
tests/                # Unit tests for the pure logic
```

See [`CLAUDE.md`](CLAUDE.md) for the architecture, the chapter/beat schema, and
how to author new chapters and puzzles.

---

## Development

```bash
python3 -m pytest      # Run the tests (pure logic + cairo scenery; no display needed)
meson test -C _build   # Validate the desktop file and AppStream metainfo
GTK_DEBUG=interactive python3 -m the_man_who_counted   # (from src/) GTK Inspector
```
