"""Development entry point: ``python3 -m the_man_who_counted`` (run from ``src/``)."""

from __future__ import annotations

import sys

from .main import main

if __name__ == "__main__":
    sys.exit(main())
