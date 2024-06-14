import discord
from yt_dlp import YoutubeDL

class MusicQueue:
    class SearchResult:
        def __init__(self, source: str, title: str) -> None:
            self.source = source
            self.title = title

    def __init__(self, voice_client: discord.VoiceClient) -> None:
        self._voice_client = voice_client
        self._queue = []
        self.YDL_OPTIONS = {
            "max_downloads": 1,
            "format": "bestaudio/best",
            "noplaylist": True
            }
        self.FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn"
        }
        self._onrepeat = False

    def __len__(self) -> int:
        return len(self._queue)

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
    
    @property
    def is_playing(self) -> bool:
        return self._voice_client.is_playing()

    @property
    def is_paused(self) -> bool:
        return self._voice_client.is_paused()

    @property
    def is_onrepeat(self) -> bool:
        return self._onrepeat

    @property
    def queue(self) -> list[SearchResult]:
        return self._queue

    def enqueue(self, query, is_url=True) -> SearchResult | None:
        result = self.search_youtube(query, is_url=is_url)
        if result is not None:
            self._queue.append(result)
        return result

    def dequeue(self) -> SearchResult:
        return self._queue.pop(0)

    def _done_playing(self, prev: str):
        if self._onrepeat:
            self._play(prev)
        else:
            self.play_next()

    def _play(self, source: str) -> None:
        self._voice_client.play(
            source=discord.FFmpegOpusAudio(source=source, **self.FFMPEG_OPTIONS), 
            after=lambda e=None: self._done_playing(source)
            )

    def play_next(self) -> None:
        if len(self) == 0 or self.is_playing:
            return
        source = self.dequeue().source
        self._play(source)
        
    def pause(self) -> None:
        if self.is_playing:
            self._voice_client.pause()
    
    def resume(self) -> None:
        if self.is_paused:
            self._voice_client.resume()

    def repeat(self, enable=True) -> None:
        self._onrepeat = enable

    def stop(self) -> None:
        if self.is_playing:
            self._voice_client.stop()

    def skip(self) -> None:
        if self.is_playing:
            self.stop()
            self.play_next()
    
    def clear(self) -> None:
        self.stop()
        self._queue.clear()

