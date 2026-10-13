"""Tests for the painted backgrounds (cairo only, no display needed)."""

from pathlib import Path

import cairo
import pytest

from the_man_who_counted.engine import scenery

CHAPTERS = Path(__file__).resolve().parents[1] / "src" / "the_man_who_counted" / "content" / "chapters"


@pytest.mark.parametrize("name", sorted(scenery.scene_names()))
def test_every_scene_paints(name):
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 320, 200)
    scenery.paint(name, cairo.Context(surface), 320, 200, 1.5)
    surface.flush()
    assert any(surface.get_data())  # Something was drawn


def test_unknown_scene_falls_back_to_night():
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 64, 64)
    scenery.paint("no-such-scene", cairo.Context(surface), 64, 64, 0.0)
    scenery.paint(None, cairo.Context(surface), 64, 64, 0.0)


def test_chapters_only_use_painted_scenes():
    import yaml

    for path in CHAPTERS.glob("*.yaml"):
        data = yaml.safe_load(path.read_text("utf-8"))
        arts = {beat["art"] for beat in data["beats"] if isinstance(beat, dict) and beat.get("art")}
        assert arts <= scenery.scene_names(), f"{path.name} uses unpainted art {arts - scenery.scene_names()}"
