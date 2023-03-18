import argparse
import os
import sys
from threading import Thread
from typing import Callable

import urwid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from .player import Player


class customProgressBar(urwid.ProgressBar):
    """A progress bar but without progress % on its bar."""

    def get_text(self) -> str:
        return ""


class customText(urwid.Text):
    def selectable(self) -> bool:
        """To make moving through the list possible."""
        return True

    def keypress(self, _, key: str) -> str:  # type: ignore
        global LIST_LOCK
        if key == "enter":
            LIST_LOCK = False
        elif key in ("q", "Q"):
            raise urwid.ExitMainLoop()
        return key


LIST_LOCK = True


class playerUI:
    border: list[str]
    pallete: list[tuple[str, str, str]]
    ui_object: urwid.Padding | None
    list_updated: bool
    isplayerUI: bool
    play_pause_lock: bool
    music_player: Player
    key_dict: dict[str, Callable[[], None]]
    time_text: urwid.Text
    song_text: urwid.Text
    mode_text: urwid.Text
    volume_text: urwid.Text
    list: urwid.SimpleFocusListWalker
    playlistbox: urwid.ListBox
    pb: customProgressBar
    pb_text: urwid.Text
    player_ui_object: urwid.LineBox

    def __init__(self, args: argparse.Namespace):
        self.border = ["╔", "═", "║", "╗", "╚", "║", "═", "╝"]
        self.palette = [
            ("reversed", "standout", ""),
            ("b", "black", "dark gray"),
            ("highlight", "black", "light blue"),
            ("bg", "black", "dark blue"),
        ]
        self.ui_object = None

        self.list_updated = False
        self.isplayerUI = False
        self.play_pause_lock = False
        self.music_player = Player(args)
        self.key_dict = {
            "n": self.music_player.play_next,
            "u": self.volume_up,
            "d": self.volume_down,
            " ": self.music_player.change_player_state,
        }

    def draw_ui(self) -> urwid.Padding:
        self.ui_object = self.make_player_ui()
        return self.ui_object

    def make_player_ui(self) -> urwid.Padding:
        """Draw the main player UI"""
        # Header
        vol = 10
        self.time_text = urwid.Text("--/--")
        self.song_text = urwid.Text("Playing: None", align="center")
        self.mode_text = urwid.Text("Mode: Repeat off", align="right")
        self.volume_text = urwid.Text(
            f"Volume: {vol*'█'}{vol*'░'}",
            align="right",
        )
        cols = urwid.Columns(
            [self.time_text, self.song_text, self.mode_text, self.volume_text]
        )
        head_pile = urwid.Pile([(1, urwid.Filler(cols, valign="top"))])
        # head_pile = urwid.Pile([cols])
        head_final_widget = urwid.LineBox(
            head_pile,
            "tmpl",
            "center",
            None,
            *self.border,
        )
        # body
        self.list = urwid.SimpleFocusListWalker([])
        heading = urwid.Columns(
            [
                (6, urwid.Text("Track")),
                (15, urwid.Text("Duration")),
                urwid.Text("Title"),
            ]
        )
        self.playlistbox = urwid.ListBox(self.list)
        body_pile = urwid.Pile(
            [
                (1, urwid.Filler(heading, valign="top")),
                (1, urwid.Filler(urwid.Divider())),
                self.playlistbox,
            ],
            focus_item=2,
        )
        body = urwid.LineBox(body_pile, "", "center", None, *self.border)

        # Footer Progress bar
        self.pb = customProgressBar("reversed", "highlight")
        self.pb.set_completion(0)
        self.pb_text = urwid.Text("", align="right")
        footer_widget = urwid.Columns([self.pb, (18, self.pb_text)])
        # Final player_ui object
        self.player_ui_object = urwid.Frame(
            body,
            header=head_final_widget,
            footer=footer_widget,
            focus_part="header",
        )
        self.list_updated = True
        self.isplayerUI = True

        return urwid.Padding(self.player_ui_object)

    def handle_keys(self, key: str) -> None:
        if key in ("q", "Q"):
            raise urwid.ExitMainLoop
        try:
            self.key_dict[key]()
        except KeyError:
            pass

    def volume_down(self) -> None:
        self.music_player.volume_down()
        self.update_volume_bar()

    def volume_up(self) -> None:
        self.music_player.volume_up()
        self.update_volume_bar()

    def update_volume_bar(self) -> None:
        vol = self.music_player.volume // 5
        self.volume_text.set_text(f"Volume: {vol * '█'}{(100//5 - vol) * '░'}")

    def update_name(self, loop, _) -> None:  # type: ignore
        global LIST_LOCK
        if self.list_updated:
            new_list = []
            list_data = self.music_player.get_list_data()
            n = len(str(len(list_data)))
            track_no = 1
            for item in list_data:
                new_list.append(
                    urwid.AttrMap(
                        urwid.Columns(
                            [
                                (6, urwid.Text(str(track_no).zfill(n))),
                                (15, customText(item["duration"])),
                                customText(item["title"]),
                            ],
                        ),
                        None,
                        focus_map="reversed",
                    )
                )
                track_no += 1
            self.list[:] = new_list
            self.playlistbox.set_focus(0, coming_from=None)
            self.player_ui_object.focus_position = "body"
            self.list_updated = False
            # this will run only once
            Thread(target=self.music_player.play, daemon=True).start()

        if self.isplayerUI:
            if not self.play_pause_lock:
                self.song_text.set_text(
                    "Playing:"
                    f" {self.music_player.videos[self.music_player.curr_video_idx].title}"
                )
            time = self.music_player.get_time_details()
            self.pb.set_completion(time["percentage"])
            self.time_text.set_text(f"{time['cur_time']}/{time['total_time']}")
            self.pb_text.set_text(f"{time['cur_time']}/{time['total_time']}")

            if self.music_player.prev_video_idx is not None:
                # unmark
                self.list[self.music_player.prev_video_idx].set_attr_map(
                    {"highlight": None}
                )
            # mark
            self.list[self.music_player.curr_video_idx].set_attr_map(
                {None: "highlight"}
            )

        if self.music_player.song_changed:
            self.playlistbox.set_focus(
                self.music_player.curr_video_idx, coming_from=None
            )
            self.music_player.song_changed = False

        if not LIST_LOCK:
            LIST_LOCK = True
            self.music_player.change_player_state()
            self.music_player.on_song_changed(self.playlistbox.focus_position)
            assert self.music_player.player is not None
            self.music_player.player.play_item_at_index(
                self.playlistbox.focus_position
            )

        # Call that function again in 0.1 seconds.
        loop.set_alarm_in(0.1, self.update_name)
