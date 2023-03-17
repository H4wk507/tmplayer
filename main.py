import argparse
from typing import Sequence

import urwid

from ui import playerUI


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
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
    player = playerUI(args)
    loop = urwid.MainLoop(
        player.draw_ui(), player.palette, unhandled_input=player.handle_keys
    )
    loop.set_alarm_in(0.5, player.update_name)
    loop.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
