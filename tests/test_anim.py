"""Tests for the pure animation helpers (no UI)."""

from the_man_who_counted.engine import anim


def test_typewriter_reveals_over_time():
    # At 10 cps, half a second reveals 5 of 20 chars.
    assert anim.typewriter_index(0.0, 20, cps=10) == 0
    assert anim.typewriter_index(0.5, 20, cps=10) == 5
    # Clamped to the total, never past it.
    assert anim.typewriter_index(100.0, 20, cps=10) == 20


def test_typewriter_empty_and_instant():
    assert anim.typewriter_index(1.0, 0, cps=10) == 0
    # Non-positive cps reveals everything at once.
    assert anim.typewriter_index(0.0, 12, cps=0) == 12
    assert anim.is_typewriter_done(0.0, 12, cps=0)


def test_typewriter_done():
    assert not anim.is_typewriter_done(0.4, 20, cps=10)
    assert anim.is_typewriter_done(2.0, 20, cps=10)


def test_frame_index_wraps():
    assert [anim.frame_index(t, 3) for t in range(7)] == [0, 1, 2, 0, 1, 2, 0]
    assert anim.frame_index(5, 0) == 0  # No frames -> 0


def test_easing_endpoints_and_clamp():
    assert anim.ease_in_out(0.0) == 0.0
    assert anim.ease_in_out(1.0) == 1.0
    assert anim.ease_in_out(-1.0) == 0.0
    assert anim.ease_in_out(2.0) == 1.0
    assert 0.0 < anim.ease_in_out(0.5) < 1.0


def test_lerp_uses_easing():
    assert anim.lerp(0.0, 10.0, 0.0) == 0.0
    assert anim.lerp(0.0, 10.0, 1.0) == 10.0
