import argparse
import logging
from pathlib import Path
from time import sleep

import vlc

from utils import format_time

logging.basicConfig(filename="myapp.log", level=logging.INFO)


class Video:
    title: str
    cur_time: int

    def __init__(self, path: Path, duration: int = 0):
        self.path = path
        self.duration = duration
        self.title = path.stem
        self.cur_time = 0


class Player:
    paths: list[Path]
    instance: vlc.Instance
    playlist: vlc.MediaList
    videos: list[Video]
    song_changed: bool
    prev_video_idx: int | None
    curr_video_idx: int
    volume: int
    size: int
    player: vlc.MediaListPlayer | None
    checked: bool  # TODO: better name?

    def __init__(self, args: argparse.Namespace):
        self.paths = [Path(p) for p in args.paths]
        self.instance = vlc.Instance()
        self.instance.log_unset()
        self.playlist = self.instance.media_list_new()
        self.videos = self.gather_files()
        self.song_changed = False
        self.prev_video_idx = None
        self.curr_video_idx = 0
        self.volume = 50

        self.player = None
        self.checked = False

    def on_song_changed(self, idx: int | None = None) -> None:
        # TODO: reformat this
        if idx is not None:
            self.prev_video_idx = self.curr_video_idx
            self.curr_video_idx = idx
            self.checked = True
        elif self.prev_video_idx is not None and not self.checked:
            self.prev_video_idx = self.curr_video_idx
            self.curr_video_idx += 1
        elif self.prev_video_idx is None and not self.checked:
            self.prev_video_idx = -1
        else:
            self.checked = False
        self.song_changed = True

    def play(self) -> None:
        for video in self.videos:
            m = self.instance.media_new(video.path.as_posix())
            self.playlist.add_media(m)
        self.size = len(self.playlist)
        self.player = self.instance.media_list_player_new()
        self.player.set_media_list(self.playlist)
        self.player.get_media_player().audio_set_volume(self.volume)
        media_player_events = self.player.event_manager()
        media_player_events.event_attach(
            vlc.EventType.MediaListPlayerNextItemSet,
            lambda _: self.on_song_changed(),
        )
        self.player.play()
        # wait for playlist to open
        while self.player.get_state() != vlc.State.Playing:
            sleep(0.1)
        # wait till the end of the playlist
        while self.player.get_state() not in (
            vlc.State.Ended,
            vlc.State.Stopped,
        ):
            sleep(1)

    def gather_files(self) -> list[Video]:
        """Gather all files provided in args into a single list."""
        files: list[Video] = []
        # TODO: check if file exists
        # TODO: add supported formats list
        for path in self.paths:
            if path.is_dir():
                for pth in path.iterdir():
                    if pth.is_file() and pth.suffix in (".mp3", ".flac"):
                        m = self.instance.media_new(pth.as_posix())
                        m.parse_with_options(1, 0)
                        while (
                            m.get_parsed_status() != vlc.MediaParsedStatus.done
                        ):
                            pass
                        files.append(
                            Video(pth, round(m.get_duration() / 1000))
                        )
            else:
                if path.suffix in (".mp3", ".flac"):
                    m = self.instance.media_new(path.as_posix())
                    m.parse_with_options(1, 0)
                    while m.get_parsed_status() != vlc.MediaParsedStatus.done:
                        pass
                    files.append(Video(path, round(m.get_duration() / 1000)))
        return files

    def get_time_details(self) -> dict[str, str | float]:
        # TODO: make class out of it?
        time_details: dict[str, str | float] = {}
        total_seconds = self.videos[self.curr_video_idx].duration
        time_details["total_time"] = format_time(total_seconds)

        if self.player is not None:
            cur_seconds = round(
                self.player.get_media_player().get_time() / 1000
            )
        else:
            cur_seconds = 0
        time_details["cur_time"] = format_time(cur_seconds)

        if total_seconds != 0:
            time_details["percentage"] = (cur_seconds / total_seconds) * 100
        else:
            time_details["percentage"] = 0
        return time_details

    def get_list_data(self) -> list[dict[str, str]]:
        list_data: list[dict[str, str]] = []
        for video in self.videos:
            details: dict[str, str] = {}
            details["title"] = video.title
            details["duration"] = format_time(video.duration)
            list_data.append(details)
        return list_data

    def play_next(self) -> None:
        if self.curr_video_idx < self.size - 1:
            assert self.player is not None
            self.player.next()

    def volume_up(self) -> None:
        if self.volume < 100:
            self.volume += 5
            assert self.player is not None
            self.player.get_media_player().audio_set_volume(self.volume)

    def volume_down(self) -> None:
        if self.volume > 0:
            self.volume -= 5
            assert self.player is not None
            self.player.get_media_player().audio_set_volume(self.volume)

    def change_player_state(self) -> None:
        if self.player is not None and self.player.get_state() in (
            vlc.State.Playing,
            vlc.State.Paused,
        ):
            self.player.pause()
