import discord
from yt_dlp import YoutubeDL
from random import randint

class MusicQueue:
    class RepeatMode():
        NO_REPEAT = 0
        REPEAT_ALL = 1
        REPEAT_THIS = 2

    class ShuffleMode():
        NO_SHUFFLE = 0
        NORMAL_SHUFFLE = 1
        SMART_SHUFFLE = 2 # Not yet implemented

    class SearchResult:
        def __init__(self, source: str, title: str) -> None:
            self.source = source
            self.title = title

    def __init__(self, voice_client: discord.VoiceClient) -> None:
        self._voice_client = voice_client
        self._queue: list[self.SearchResult] = []
        self.YDL_OPTIONS = {
            "max_downloads": 1,
            "format": "bestaudio/best",
            "noplaylist": True
            }
        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn"
        }
        self._repeat = self.RepeatMode.NO_REPEAT
        self._shuffle = self.ShuffleMode.NO_SHUFFLE
        self._current_pos = -1

    def __len__(self) -> int:
        return len(self._queue)

    def _in_bounds(self, index: int) -> bool:
        return index >= 0 and index < len(self._queue)

    def _next_pos(self, diff=0):
        pos = self._current_pos + diff
        if self._repeat == self.RepeatMode.REPEAT_ALL:
            pos %= len(self)
        return pos
            
    def _done_playing(self):
        if self._repeat == self.RepeatMode.REPEAT_THIS:
            self.play(self._current_pos)
        elif self._shuffle != self.ShuffleMode.NO_SHUFFLE:
            self.play(randint(0, len(self)))
        else:
            self.play_next()

    @property
    def is_playing(self) -> bool:
        return self._voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self._voice_client.is_paused()

    @property
    def repeat_mode(self) -> int:
        return self._repeat

    @property
    def shuffle_mode(self) -> int:
        return self._shuffle

    @property
    def queue(self) -> list[SearchResult]:
        return self._queue

    @property
    def pos(self):
        return self._current_pos

    def search_youtube(self, query: str, is_url=True) -> SearchResult | None:
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                query = query if is_url else f"ytsearch:{query}"
                response = ydl.extract_info(query, download=False)["entries"][0]
            except Exception as e:
                print(e)
                return None
        return self.SearchResult(
            response["url"],
            response.get("title", "Unknown title")
        )
    
    def enqueue(self, query, is_url=True) -> SearchResult | None:
        result = self.search_youtube(query, is_url=is_url)
        if result is not None:
            self._queue.append(result)
        return result

    def dequeue(self) -> SearchResult:
        return self._queue.pop(0)

    def play(self, pos: int) -> None:
        if not self._in_bounds(pos):
            return
        if self.is_playing:
            self.stop()
        self._current_pos = pos
        source = self._queue[pos].source
        self._voice_client.play(
            source=discord.FFmpegOpusAudio(source=source, **self.FFMPEG_OPTIONS), 
            after=lambda e=None: self._done_playing()
            )

    def play_next(self) -> None:
        self.play(self._next_pos(1))
    
    def play_prev(self) -> None:
        self.play(self._next_pos(-1))

    def pause(self) -> None:
        if self.is_playing:
            self._voice_client.pause()
    
    def resume(self) -> None:
        if self.is_paused:
            self._voice_client.resume()

    def repeat(self, mode: int) -> None:
        self._repeat = mode

    def repeat_next(self) -> None:
        self.repeat((self._repeat + 1) % 3)

    def shuffle(self, mode: int) -> None:
        self._shuffle = mode

    def shuffle_next(self):
        self.shuffle((self._shuffle + 1) % 3)

    def stop(self) -> None:
        if self.is_playing:
            self._voice_client.stop()

    def clear(self) -> None:
        self.stop()
        self._queue.clear()
