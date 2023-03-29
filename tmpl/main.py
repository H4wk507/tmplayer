#!/usr/bin/env python3

import argparse
import os
import sys
from typing import Sequence

import urwid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tmpl.ui import PlayerUI
from tmpl.version import __version__


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        type=str,
        nargs="+",
        help="Path(s) to video(s)/director(y)/(ies) to play.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    ui = PlayerUI(args)
    loop = urwid.MainLoop(
        ui.draw_ui(), ui.palette, unhandled_input=ui.handle_keys
    )
    loop.set_alarm_in(0, ui.main)
    loop.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
