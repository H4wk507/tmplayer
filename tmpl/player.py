import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from random import randint
from time import sleep

import vlc

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    player: vlc.MediaPlayer
    supported_formats: tuple[str, ...]
    videos: list[Video]
    song_changed: bool
    prev_video_idx: int | None
    curr_video_idx: int
    volume: int
    volume_step: int
    random_mode: bool
    loop_mode: bool
    repeat_mode: bool

    def __init__(self, args: argparse.Namespace):
        # disable error output
        os.environ["VLC_VERBOSE"] = "-1"
        self.paths = [Path(p) for p in args.paths]
        self.instance = vlc.Instance()
        self.instance.log_unset()
        self.supported_formats = (
            ".mp3",
            ".flac",
            ".m4a",
            ".aac",
            ".alac",
            ".ogg",
            ".wav",
        )
        self.videos = self.gather_files()
        self.song_changed = False
        self.prev_video_idx = None
        self.curr_video_idx = 0
        self.volume = 50
        self.volume_step = 5
        self.player = vlc.MediaPlayer()
        self.player.audio_set_volume(self.volume)
        self.random_mode = False
        self.loop_mode = False
        self.repeat_mode = False
        # self.played_indices = set()

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
            duration_ms = self.get_file_duration(path)
            files.append(Video(path, round(duration_ms / 1000)))

    def get_file_duration(self, path: Path) -> int:
        """Get file duration in ms."""
        m = self.instance.media_new(path.as_posix())
        m.parse_with_options(1, 0)
        while m.get_parsed_status() != vlc.MediaParsedStatus.done:
            pass
        return m.get_duration()  # type: ignore

    def play(self) -> None:
        # TODO: handle modes like on youtube playlist
        while self.curr_video_idx < len(self.videos):
            self.set_player_media()
            self.player.play()
            self.wait_for_open()
            self.wait_for_end()
            if self.repeat_mode:
                continue
            self.song_changed = True
            self.prev_video_idx = self.curr_video_idx
            if self.random_mode:
                self.curr_video_idx = randint(0, len(self.videos) - 1)
            elif self.loop_mode:
                self.curr_video_idx += 1
                self.curr_video_idx %= len(self.videos)
            else:
                self.curr_video_idx += 1
        self.curr_video_idx -= 1

    def set_player_media(self) -> None:
        media = self.instance.media_new(
            self.videos[self.curr_video_idx].path.as_posix()
        )
        self.player.set_media(media)

    def wait_for_open(self) -> None:
        """Wait for the player to open."""
        assert self.player is not None
        while self.player.get_state() != vlc.State.Playing:
            sleep(0.1)

    def wait_for_end(self) -> None:
        """Wait for the player to end."""
        assert self.player is not None
        while self.player.get_state() not in (
            vlc.State.Ended,
            vlc.State.Stopped,
        ):
            sleep(1)

    def get_time_details(self) -> TimeDetails:
        total_seconds = self.videos[self.curr_video_idx].duration
        curr_seconds = (
            round(self.player.get_time() / 1000)
            if self.player is not None
            else 0
        )
        return TimeDetails(
            Player.format_time(total_seconds),
            Player.format_time(curr_seconds),
            (curr_seconds / total_seconds) * 100 if total_seconds != 0 else 0,
        )

    def get_list_data(self) -> list[ListData]:
        return [
            ListData(idx, Player.format_time(video.duration), video.title)
            for idx, video in enumerate(self.videos, 1)
        ]

    @staticmethod
    def format_time(seconds: int) -> str:
        """Format time in seconds to a string."""
        hours = seconds // 3600
        seconds = seconds % 3600
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def volume_up(self) -> None:
        if self.player is not None and self.volume < 100:
            self.volume += self.volume_step
            self.player.audio_set_volume(self.volume)

    def volume_down(self) -> None:
        if self.player is not None and self.volume > 0:
            self.volume -= self.volume_step
            self.player.audio_set_volume(self.volume)

    def change_player_state(self) -> None:
        if self.player is not None and self.player.get_state() in (
            vlc.State.Playing,
            vlc.State.Paused,
        ):
            self.player.pause()
