import sys
import subprocess
from anthropic import beta_tool

class JarvisSystem:
    def __init__(self):
        self.os = sys.platform
        self.processes = {}
        result = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True)
        self.muted = "MUTED" in result.stdout

    def open_app(self, app: str):
        if self.os == "Linux":
            self.processes[app] = subprocess.Popen(["xdg-open", app])
        elif self.os == "Windows":
            self.processes[app] = subprocess.run(f"start {app}", shell=True)

    def close_app(self, app: str):
        if app in self.processes:
            self.processes[app].kill()
            del self.processes[app]

    def set_volume_linux(self, volume: float):
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{volume}%"])

    def adjust_volume_linux(self, volume: float):
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"+{volume}"])

    def mute(self):
        subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
        self.muted = not self.muted


system = JarvisSystem()

@beta_tool
def open_app(app: str):
    """Open an application on the system.
    Args:
        app: The name or path of the application to open
    Returns:
        Confirmation that the app was opened
    """
    try:
        system.open_app(app)
        return f"Successfully opened {app}"
    except Exception:
        return f"Failed to open {app}"

@beta_tool
def close_app(app: str):
    """Close a running application on the system.
    Args:
        app: The name of the application to close
    Returns:
        Confirmation that the app was closed
    """
    try:
        system.close_app(app)
        return f"Successfully closed {app}"
    except Exception:
        return f"Failed to close {app}"

@beta_tool
def set_volume_linux(volume: float):
    """Set the system volume to a specific level.
    Args:
        volume: The volume level to set (0-100)
    Returns:
        Confirmation that the volume was changed
    """
    try:
        system.set_volume_linux(volume)
        return f"Successfully changed volume to {volume}"
    except Exception:
        return f"Failed to change to {volume}"

@beta_tool
def adjust_volume_linux(volume: float):
    """Adjust the system volume up or down by a relative amount.
    Args:
        volume: The amount to adjust the volume by, positive to increase, negative to decrease
    Returns:
        Confirmation that the volume was adjusted
    """
    try:
        system.adjust_volume_linux(volume)
        return f"Successfully changed volume by {volume}"
    except Exception:
        return f"Failed to change by {volume}"

@beta_tool
def mute():
    """Toggle mute on the system audio.
    Returns:
        Confirmation that the audio was muted or unmuted
    """
    try:
        system.mute()
        return f"Successfully muted"
    except Exception:
        return f"Failed to mute"


