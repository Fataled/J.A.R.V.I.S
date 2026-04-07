import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from tools import tool


class Spotify:
    def __init__(self):
        load_dotenv()
        scope = (
            "playlist-read-private playlist-modify-private playlist-modify-public "
            "playlist-read-collaborative user-library-read user-read-playback-state "
            "user-modify-playback-state user-read-currently-playing user-top-read"
        )
        self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            os.getenv("SPOTIFY_ID"),
            os.getenv("SPOTIFY_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope=scope
        ))

    def _find_track(self, song_name: str, artist_name: str = None):
        query = f"track:{song_name}"
        if artist_name:
            query += f" artist:{artist_name}"
        results = self.spotify.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]
        if not tracks:
            return None
        track = tracks[0]
        return {"name": track["name"], "artist": track["artists"][0]["name"], "uri": track["uri"]}


    def play(self, uri: str):
        """Play a song on Spotify.

        Args:
            uri: The Spotify URI of the song to play
        """
        devices = self.spotify.devices()["devices"]
        if devices:
            self.spotify.start_playback(device_id=devices[0]["id"], uris=[uri])
        return "Playing"

    @tool
    def search_and_play(self, song_name: str, artist_name: str = ""):
        """Search for a song and play it.

        Args:
            song_name: The name of the song to search for
            artist_name: Optional artist name to narrow the search
        """
        track = self._find_track(song_name, artist_name or None)
        if not track:
            return f"Could not find {song_name}"
        self.play(uri=track["uri"])
        return f"Playing {track['name']} by {track['artist']}"

    @tool
    def pause(self):
        """Pause Spotify playback."""
        self.spotify.pause_playback()
        return "Paused"

    @tool
    def resume(self):
        """Resume Spotify playback."""
        devices = self.spotify.devices()["devices"]
        if devices:
            self.spotify.start_playback(device_id=devices[0]["id"])
        return "Resumed"

    @tool
    def currently_playing(self):
        """Get the currently playing track."""
        result = self.spotify.currently_playing()
        if not result or not result.get("item"):
            return "Nothing playing"
        item = result["item"]
        return f"{item['name']} by {item['artists'][0]['name']}"

    @tool
    def skip_track(self):
        """Skip to the next track."""
        self.spotify.next_track()
        return "Skipped"

    @tool
    def previous_track(self):
        """Go to the previous track."""
        self.spotify.previous_track()
        return "Previous track"

spotify = Spotify()
print(spotify.play.__func__)
