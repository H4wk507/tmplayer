import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import vlc

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tmpl.utils import format_time

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class TimeDetails:
    duration: str
    curr_time: str
    percentage: float


@dataclass
class ListData:
    index: int
    duration: str
    title: str


class Video:
    title: str
    curr_time: int

    def __init__(self, path: Path, duration: int):
        self.path = path
        self.duration = duration
        self.title = path.stem
        self.curr_time = 0


class Player:
    paths: list[Path]
    instance: vlc.Instance
    playlist: vlc.MediaList | None
    player: vlc.MediaListPlayer | None
    supported_formats: tuple[str, ...]
    videos: list[Video]
    song_changed: bool
    prev_video_idx: int | None
    curr_video_idx: int
    volume: int
    volume_step: int
    prev_pressed: bool
    next_pressed: bool
    enter_pressed_idx: int | None

    def __init__(self, args: argparse.Namespace):
        self.paths = [Path(p) for p in args.paths]
        self.instance = vlc.Instance()
        self.instance.log_unset()
        self.playlist = None
        self.player = None
        self.supported_formats = (".mp3", ".flac")
        self.videos = self.gather_files()
        self.song_changed = False
        self.prev_video_idx = None
        self.curr_video_idx = 0
        self.volume = 50
        self.volume_step = 5
        self.prev_pressed = False
        self.next_pressed = False
        self.enter_pressed_idx = None

    def gather_files(self) -> list[Video]:
        """Gather all files provided in args into a single list."""
        files: list[Video] = []
        for path in self.paths:
            if path.is_dir():
                self.gather_dir(path, files)
            elif path.is_file():
                self.gather_file(path, files)
        if len(files) == 0:
            LOGGER.error("Could not parse any files.")
            sys.exit(1)
        else:
            return files

    def gather_dir(self, path: Path, files: list[Video]) -> None:
        for pth in path.iterdir():
            if pth.is_file():
                self.gather_file(pth, files)

    def gather_file(self, path: Path, files: list[Video]) -> None:
        if path.suffix in self.supported_formats:
            m = self.instance.media_new(path.as_posix())
            m.parse_with_options(1, 0)
            while m.get_parsed_status() != vlc.MediaParsedStatus.done:
                pass
            files.append(Video(path, round(m.get_duration() / 1000)))

    def play(self) -> None:
        self.init_playlist()
        assert self.player is not None
        self.player.play()
        self.wait_for_open()
        self.wait_for_end()

    def init_playlist(self) -> None:
        self.playlist = self.instance.media_list_new()
        for video in self.videos:
            media = self.instance.media_new(video.path.as_posix())
            self.playlist.add_media(media)
        self.init_player()

    def init_player(self) -> None:
        self.player = self.instance.media_list_player_new()
        self.player.set_media_list(self.playlist)
        self.player.get_media_player().audio_set_volume(self.volume)
        player_events = self.player.event_manager()
        player_events.event_attach(
            vlc.EventType.MediaListPlayerNextItemSet,
            lambda _: self.on_song_changed(),
        )

    def wait_for_open(self) -> None:
        """Wait for the playlist to open."""
        assert self.player is not None
        while self.player.get_state() != vlc.State.Playing:
            sleep(0.1)

    def wait_for_end(self) -> None:
        """Wait for the playlist to end."""
        assert self.player is not None
        while self.player.get_state() not in (
            vlc.State.Ended,
            vlc.State.Stopped,
        ):
            sleep(1)

    def on_song_changed(self) -> None:
        if self.enter_pressed_idx is not None:
            self.prev_video_idx = self.curr_video_idx
            self.curr_video_idx = self.enter_pressed_idx
            self.enter_pressed_idx = None
        elif self.next_pressed:
            self.prev_video_idx = self.curr_video_idx
            self.curr_video_idx += 1
            self.next_pressed = False
        elif self.prev_pressed:
            self.prev_video_idx = self.curr_video_idx
            self.curr_video_idx -= 1
            self.prev_pressed = False
        elif self.prev_video_idx is not None:
            self.prev_video_idx = self.curr_video_idx
            self.curr_video_idx += 1
        else:
            self.prev_video_idx = self.curr_video_idx
        self.song_changed = True

    def play_prev(self) -> None:
        if self.player is not None and self.curr_video_idx > 0:
            self.prev_pressed = True
            self.player.previous()

    def get_time_details(self) -> TimeDetails:
        total_seconds = self.videos[self.curr_video_idx].duration
        curr_seconds = (
            round(self.player.get_media_player().get_time() / 1000)
            if self.player is not None
            else 0
        )
        return TimeDetails(
            format_time(total_seconds),
            format_time(curr_seconds),
            (curr_seconds / total_seconds) * 100 if total_seconds != 0 else 0,
        )

    def get_list_data(self) -> list[ListData]:
        return [
            ListData(idx, format_time(video.duration), video.title)
            for idx, video in enumerate(self.videos, 1)
        ]

    def play_next(self) -> None:
        if (
            self.player is not None
            and self.curr_video_idx < len(self.videos) - 1
        ):
            self.next_pressed = True
            self.player.next()

    def volume_up(self) -> None:
        if self.player is not None and self.volume < 100:
            self.volume += self.volume_step
            self.player.get_media_player().audio_set_volume(self.volume)

    def volume_down(self) -> None:
        if self.player is not None and self.volume > 0:
            self.volume -= self.volume_step
            self.player.get_media_player().audio_set_volume(self.volume)

    def change_player_state(self) -> None:
        if self.player is not None and self.player.get_state() in (
            vlc.State.Playing,
            vlc.State.Paused,
        ):
            self.player.pause()
