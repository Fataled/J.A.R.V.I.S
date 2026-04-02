from dotenv import load_dotenv
import os
import spotipy
from anthropic import beta_tool
from spotipy.oauth2 import SpotifyOAuth

class JarvisSpotify:
    def __init__(self):
        load_dotenv()

        spotify_id = os.getenv("SPOTIFY_ID")
        spotify_secret = os.getenv("SPOTIFY_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

        scope = ("playlist-read-private "
                 "playlist-modify-private "
                 "playlist-modify-public "
                 "playlist-read-collaborative "
                 "user-library-read "
                 "user-read-playback-state "
                 "user-modify-playback-state "
                 "user-read-currently-playing "
                 "user-top-read")

        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(spotify_id, spotify_secret, redirect_uri=redirect_uri, scope=scope))

    def play(self, uri: str):
        """Play a song on Spotify.

           Args:
               uri: The name of the song to play
           Returns:
               Confirmation that the song is playing
           """
        devices = self.spotify.devices()["devices"]
        if devices:
            device_id = devices[0]["id"]
            self.spotify.start_playback(device_id=device_id, uris=[uri])




    def pause(self):
        self.spotify.pause_playback()
        return {"role": "user",
                "content": "Confirm to me that you just paused the music in your usual manner."}

    def resume(self):
        self.spotify.start_playback()
        return {"role": "user", "content": "Confirm to me that you just resumed the music in your usual manner." }

    def currently_playing(self):
        return self.spotify.currently_playing()


    def _find_track(self, song_name, artist_name=None):
        query = f"track:{song_name}"
        if artist_name:
            query += f" artist:{artist_name}"
        results = self.spotify.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]
        if not tracks:
            return None
        track = tracks[0]
        return {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "uri": track["uri"]
        }

spotify_client = JarvisSpotify()

@beta_tool
def clear_and_play(song_name: str, artist_name: str = None) -> str:
    """Play a song on Spotify.
    Args:
        song_name: The name of the song to play
        artist_name: The artist name (optional)
    Returns:
        Confirmation that the song is playing
    """
    track = spotify_client._find_track(song_name, artist_name)
    if track:
        spotify_client.spotify.start_playback(uris=[track["uri"]])
        return f"Now playing {track['name']} by {track['artist']}"
    return "Track not found"

@beta_tool
def play(song_name: str, artist_name: str = None) -> str:
    """Play a song on Spotify."""
    track = spotify_client._find_track(song_name, artist_name)
    import time
    if track:
        for attempt in range(5):
            try:
                spotify_client.play(track["uri"])
                return f"now playing {track['name']} by {track['artist']}"
            except Exception as e:
                if "NO_ACTIVE_DEVICE" in str(e):
                    time.sleep(2)  # wait for Spotify to finish loading
                else:
                    raise
        return "Spotify never became active"
    return "Track not found"

@beta_tool
def pause() -> str:
    try:
        spotify_client.pause()
        return f"Paused"
    except Exception as e:
        return f"An error occurred while pausing your music. reason {e}"

@beta_tool
def resume() -> str:
    try:
        spotify_client.resume()
        return f"Resumed"
    except Exception as e:
        return f"An error occurred while resuming your music. reason {e}"

@beta_tool
def currently_playing() -> str:
    try:
        playing = spotify_client.currently_playing()
        return f"Confirm to me whether music is currently playing or not using {playing}"
    except Exception as e:
        return f"Inform me that you just played in your usual manner. reason {e}"