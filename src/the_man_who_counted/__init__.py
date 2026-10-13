"""The Man Who Counted — a GNOME visual novel inspired by Malba Tahan's book.

This is pre-alpha software with no releases yet. The game is published as
numbered builds: when cutting a new one, bump ``BUILD`` here and the matching
version in ``meson.build`` and the metainfo ``<release>``.
"""

STAGE = "pre-alpha"
BUILD = 1

__version__ = f"{STAGE}.{BUILD}"
BUILD_LABEL = f"Pre-alpha · Build {BUILD}"
