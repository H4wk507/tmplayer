import argparse
import os
import sys
from threading import Thread
from typing import Callable

import urwid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tmpl.player import Player


class progressBar(urwid.ProgressBar):
    """A progress bar but without progress percentage on it."""

    def get_text(self) -> str:
        return ""


class selectableText(urwid.Text):
    def selectable(self) -> bool:
        return True

    def keypress(self, _, key: str) -> str:  # type: ignore
        global LIST_LOCK
        if key == "enter":
            LIST_LOCK = False
        return key


LIST_LOCK = True


class PlayerUI:
    border: list[str]
    pallete: list[tuple[str, str, str]]
    ui_object: urwid.Padding | None
    list_updated: bool
    play_pause_lock: bool
    music_player: Player
    key_dict: dict[str, Callable[[], None]]
    time_text: urwid.Text
    song_text: urwid.Text
    mode_text: urwid.Text
    volume_text: urwid.Text
    list: urwid.SimpleFocusListWalker
    playlistbox: urwid.ListBox
    pb: progressBar
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
        self.play_pause_lock = False
        self.music_player = Player(args)
        self.key_dict = {
            "n": self.music_player.play_next,
            "u": self.volume_up,
            "d": self.volume_down,
            " ": self.music_player.change_player_state,
        }

    def draw_ui(self) -> urwid.Padding:
        self.ui_object = self.get_player_ui()
        list_data = self.music_player.get_list_data()
        zero_pad = len(str(len(list_data)))
        new_list = [
            urwid.AttrMap(
                urwid.Columns(
                    [
                        (6, urwid.Text(str(video.index).zfill(zero_pad))),
                        (15, urwid.Text(video.duration)),
                        selectableText(video.title),
                    ]
                ),
                None,
                "reversed",
            )
            for video in list_data
        ]
        self.list[:] = new_list
        self.playlistbox.set_focus(0)
        self.start_playing()
        return self.ui_object

    def get_player_ui(self) -> urwid.Padding:
        """Draw the main player UI."""
        header = self.get_header()
        body = self.get_body()
        footer = self.get_footer()
        self.player_ui_object = urwid.Frame(body, header, footer)
        return urwid.Padding(self.player_ui_object)

    def get_header(self) -> urwid.LineBox:
        vol = 100 // self.music_player.volume_step
        self.time_text = urwid.Text("--/--")
        self.song_text = urwid.Text("Playing: None", "center")
        self.mode_text = urwid.Text("Mode: Repeat off", "right")
        self.volume_text = urwid.Text(
            f"Volume: {vol//2*'█'}{vol//2*'░'}", "right"
        )
        cols = urwid.Columns(
            [self.time_text, self.song_text, self.mode_text, self.volume_text]
        )
        head_pile = urwid.Pile([(1, urwid.Filler(cols, valign="top"))])
        # head_pile = urwid.Pile([cols])
        header = urwid.LineBox(head_pile, "tmpl", "center", None, *self.border)
        return header

    def get_body(self) -> urwid.LineBox:
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
                (1, urwid.Filler(heading, "top")),
                (1, urwid.Filler(urwid.Divider())),
                self.playlistbox,
            ]
        )
        body = urwid.LineBox(body_pile, "", "center", None, *self.border)
        return body

    def get_footer(self) -> urwid.Columns:
        self.pb = progressBar("reversed", "highlight")
        self.pb.set_completion(0)
        self.pb_text = urwid.Text("", "right")
        footer = urwid.Columns([self.pb, (18, self.pb_text)])
        return footer

    def start_playing(self) -> None:
        """Start playing the music in a separate thread."""
        Thread(target=self.music_player.play, daemon=True).start()

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
        vol = self.music_player.volume // self.music_player.volume_step
        vol_complement = 100 // self.music_player.volume_step - vol
        self.volume_text.set_text(f"Volume: {vol*'█'}{vol_complement*'░'}")

    def main(self, loop, _) -> None:  # type: ignore
        global LIST_LOCK
        if not self.play_pause_lock:
            self.song_text.set_text(
                "Playing:"
                f" {self.music_player.videos[self.music_player.curr_video_idx].title}"
            )
        td = self.music_player.get_time_details()
        self.pb.set_completion(td.percentage)
        self.time_text.set_text(f"{td.curr_time}/{td.duration}")
        self.pb_text.set_text(f"{td.curr_time}/{td.duration}")

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
            if self.music_player.player is not None:
                self.music_player.player.play_item_at_index(
                    self.playlistbox.focus_position
                )

        # Call that function again in 0.1 seconds.
        loop.set_alarm_in(0.1, self.main)
