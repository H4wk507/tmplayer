import argparse
import os
import sys
from random import randint
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
        return key


class PlayerUI:
    border: tuple[str, ...]
    pallete: tuple[tuple[str, str, str]]
    paused: bool
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

    def __init__(self, args: argparse.Namespace):
        self.border = ("╔", "═", "║", "╗", "╚", "║", "═", "╝")
        self.palette = (
            ("reversed", "standout", ""),
            ("b", "black", "dark gray"),
            ("highlight", "black", "light blue"),
            ("bg", "black", "dark blue"),
        )
        self.paused = False
        self.music_player = Player(args)
        self.key_dict = {
            "n": self.play_next,
            "p": self.play_prev,
            "u": self.volume_up,
            "d": self.volume_down,
            "r": self.toggle_random_mode,
            "1": self.toggle_default_mode,
            "2": self.toggle_loop_mode,
            "3": self.toggle_repeat_mode,
            " ": self.change_player_state,
            "enter": self.on_enter_pressed,
        }

    def draw_ui(self) -> urwid.Padding:
        ui_object = self.get_player_ui()
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
        return ui_object

    def get_player_ui(self) -> urwid.Padding:
        """Draw the main player UI."""
        header = self.get_header()
        body = self.get_body()
        footer = self.get_footer()
        player_ui_object = urwid.Frame(body, header, footer)
        return urwid.Padding(player_ui_object)

    def get_header(self) -> urwid.LineBox:
        self.time_text = urwid.Text("--/--")
        self.song_text = urwid.Text("Playing: None", "center")
        self.mode_text = urwid.Text("Mode: Default", "right")
        self.volume_text = urwid.Text(
            f"Volume: {self.music_player.volume}%/100%", "right"
        )
        cols = urwid.Columns(
            [self.time_text, self.song_text, self.mode_text, self.volume_text]
        )
        head_pile = urwid.Pile([(1, urwid.Filler(cols, valign="top"))])
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

    def play_prev(self) -> None:
        """Play the previous song."""
        if self.music_player.curr_video_idx == 0:
            return
        self.on_new_song()
        if self.music_player.random_mode:
            self.music_player.curr_video_idx = randint(
                0, len(self.music_player.videos) - 1
            )
        else:
            self.music_player.curr_video_idx -= 1
        self.play_new()

    def play_next(self) -> None:
        """Play the next song."""
        if (
            self.music_player.curr_video_idx
            == len(self.music_player.videos) - 1
        ):
            return
        self.on_new_song()
        if self.music_player.random_mode:
            self.music_player.curr_video_idx = randint(
                0, len(self.music_player.videos) - 1
            )
        else:
            self.music_player.curr_video_idx += 1
        self.play_new()

    def on_enter_pressed(self) -> None:
        self.on_new_song()
        self.music_player.curr_video_idx = self.playlistbox.focus_position
        self.play_new()

    def on_new_song(self) -> None:
        self.paused = False
        self.music_player.repeat_mode = False
        self.music_player.loop_mode = False
        self.change_mode_text()
        self.music_player.prev_video_idx = self.music_player.curr_video_idx

    def play_new(self) -> None:
        """Play the next song currently at curr_video_idx."""
        self.music_player.song_changed = True
        assert self.music_player.player is not None
        self.music_player.player.stop()
        self.music_player.set_player_media()
        self.music_player.player.play()

    def volume_up(self) -> None:
        self.music_player.volume_up()
        self.update_volume_bar()

    def volume_down(self) -> None:
        self.music_player.volume_down()
        self.update_volume_bar()

    def toggle_random_mode(self) -> None:
        self.music_player.random_mode = not self.music_player.random_mode
        self.change_mode_text()

    def toggle_default_mode(self) -> None:
        self.music_player.random_mode = False
        self.music_player.loop_mode = False
        self.music_player.repeat_mode = False
        self.change_mode_text()

    def toggle_loop_mode(self) -> None:
        self.music_player.loop_mode = not self.music_player.loop_mode
        self.music_player.repeat_mode = False
        self.change_mode_text()

    def toggle_repeat_mode(self) -> None:
        self.music_player.repeat_mode = not self.music_player.repeat_mode
        self.music_player.loop_mode = False
        self.change_mode_text()

    def change_mode_text(self) -> None:
        options = []
        if self.music_player.random_mode:
            options.append("Random")
        if self.music_player.repeat_mode:
            options.append("Repeat")
        if self.music_player.loop_mode:
            options.append("Loop")
        if len(options) == 0:
            options.append("Default")
        text = "Mode: " + " & ".join(options)
        self.mode_text.set_text(text)

    def change_player_state(self) -> None:
        """Handle the pause/play button press."""
        self.paused = not self.paused
        self.music_player.change_player_state()

    def update_volume_bar(self) -> None:
        self.volume_text.set_text(f"Volume: {self.music_player.volume}%/100%")

    def main(self, loop: urwid.MainLoop, _) -> None:  # type: ignore
        curr_idx = self.music_player.curr_video_idx
        if self.paused:
            self.song_text.set_text(
                f"[Paused] {self.music_player.videos[curr_idx].title}"
            )
        else:
            self.song_text.set_text(
                f"Playing: {self.music_player.videos[curr_idx].title}"
            )

        td = self.music_player.get_time_details()
        self.pb.set_completion(td.percentage)
        self.time_text.set_text(f"{td.curr_time}/{td.duration}")
        self.pb_text.set_text(f"{td.curr_time}/{td.duration}")

        if self.music_player.prev_video_idx is not None:
            self.list[self.music_player.prev_video_idx].set_attr_map(
                {"highlight": None}
            )
        self.list[self.music_player.curr_video_idx].set_attr_map(
            {None: "highlight"}
        )

        if self.music_player.song_changed:
            self.playlistbox.set_focus(self.music_player.curr_video_idx)
            self.music_player.song_changed = False

        # Call that function again in 0.1 seconds.
        loop.set_alarm_in(0.1, self.main)
