import os
import sys
import subprocess
import time
from anthropic import beta_tool
import threading
import json
import psutil
import GPUtil
#from pycaw.utils import AudioUtilities


class JarvisSystem:
    CLIPS_DIR = os.path.expanduser("~/Videos/JarvisClips/")

    PROCESS_BLACKLIST = {
        "systemd", "dbus", "pipewire", "wireplumber",
        "hyprland", "waybar", "sddm", "login", "bash",
        "zsh", "fish", "ssh", "gpg-agent", "polkit",
        "hyprpaper", "dunst", "hypridle", "hyprlock",
        "xdg-desktop-portal", "at-spi", "gvfsd",
        "python3", "python", "wf-recorder",
        "pulseaudio", "pipewire-pulse", "blueman",
        "nm-applet", "NetworkManager", "wpa_supplicant"
    }

    def __init__(self):
        self.os = sys.platform
        self.processes = {}
        self.muted = False
        self.recorder = None
        self.protected_pids = {os.getpid()}
        self.CLIPS_DIR = os.path.expanduser("~/Videos/JarvisClips/")
        os.makedirs(self.CLIPS_DIR, exist_ok=True)

        if self.os == "linux":
            result = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True)
            self.muted = "MUTED" in result.stdout
            self.recording_thread = threading.Thread(target=self.start_recording_linux, daemon=True)
        elif self.os == "win32":
            self.recording_thread = threading.Thread(target=self.start_recording_windows, daemon=True)
            self.device = AudioUtilities.GetSpeakers()
            self.volume = self.device.EndpointVolume

        self.recording_thread.start()

    def get_os(self):
        return self.os

    def open_app(self, app: str):
        print(f"Attempting to open: '{app}' OS: {self.os}")
        try:
            if self.os == "linux":
                proc = subprocess.Popen([app.lower()])
            elif self.os == "win32":
                proc = subprocess.Popen(f"start {app}", shell=True)
            self.processes[app] = proc
            return f"Opened {app} with PID {proc.pid}"
        except FileNotFoundError:
            raise Exception(f"Could not find application: {app}")

    def close_app(self, app: str):
        if app in self.processes:
            self.processes[app].kill()
            del self.processes[app]
            return True
        else:
            return False

    def kill_process(self, name: str):
        killed = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if name.lower() in proc.name().lower():
                    if not self.is_protected(proc):
                        proc.kill()
                        killed.append(proc.name())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return killed

    def is_protected(self, proc: psutil.Process):
        try:
            username = proc.username()
            login = os.getlogin()
            if proc.pid in self.protected_pids:
                return True
            if proc.name().lower() in JarvisSystem.PROCESS_BLACKLIST:
                return True
            if proc.uids().real == 0:
                return True
            if username != login:
                print(f"Skipping {proc.name()} - owner: {username} vs {login}")
                return True
            return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return True

    def close_all_except(self, keep: list[str]):
        keep_lower = [k.lower() for k in keep]
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                if self.is_protected(proc):
                    print(f"Protected: {proc.name()}")
                    continue
                if any(k in proc.name().lower() for k in keep_lower):
                    print(f"Keeping: {proc.name()}")
                    continue
                print(f"Killing: {proc.name()}")
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    @staticmethod
    def set_volume_linux(volume: float):
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{volume}%"])

    @staticmethod
    def adjust_volume_linux(volume: float):
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"+{volume}"])

    def set_volume_windows(self, volume: float):
        self.volume.SetMasterVolumeLevelScalar(volume / 100, None)

    def adjust_volume_windows(self, volume: float):
        current = self.volume.GetMasterVolumeLevelScalar()
        new = max(0.0, min(1.0, current + (volume / 100)))
        self.volume.SetMasterVolumeLevelScalar(new, None)

    def mute_windows(self):
        self.muted = not self.muted
        self.volume.SetMute(self.muted, None)

    def mute_linux(self):
        subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
        self.muted = not self.muted

    @staticmethod
    def get_encoder():
        # try GPU first, fall back to CPU
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        if "h264_nvenc" in result.stdout:
            return "h264_nvenc"
        elif "h264_amf" in result.stdout:  # AMD
            return "h264_amf"
        else:
            return "libx264"

    @staticmethod
    def get_focused_monitor():
        result = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True)
        if not result.stdout.strip():
            return "DP-2"
        try:
            monitors = json.loads(result.stdout)
            return next((m["name"] for m in monitors if m["focused"]), "DP-2")
        except json.JSONDecodeError:
            return "DP-2"

    def start_recording_linux(self):
        monitor = self.get_focused_monitor()
        encoder = self.get_encoder()
        self.recorder = subprocess.Popen(
            ["wf-recorder", "-o", monitor, "-c", encoder, "-f", "/tmp/jarvis_recording.mp4"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.protected_pids.add(self.recorder.pid)

    def start_recording_windows(self):
        encoder = self.get_encoder()
        fps = "30" if encoder == "libx264" else "60"
        self.recorder = subprocess.Popen(
            ["ffmpeg", "-f", "gdigrab", "-framerate", fps, "-i", "desktop",
             "-c:v", encoder, "-preset", "ultrafast",
             "-y", os.path.join(os.environ.get("TEMP", "/tmp"), "jarvis_recording.mp4")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.protected_pids.add(self.recorder.pid)

    def jarvis_clip_that(self, filename: str):
        temp_file = os.path.join(os.environ.get("TEMP", "/tmp"), "jarvis_recording.mp4")
        output_path = os.path.join(self.CLIPS_DIR, f"{filename}.mp4")
        subprocess.run([
            "ffmpeg", "-sseof", "-30",
            "-i", temp_file,
            "-c", "copy",
            "-y", output_path,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path

    def stop_recording(self):
        if hasattr(self, "recorder"):
            self.recorder.terminate()


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
        if system.close_app(app):
            return f"Successfully closed that was opened by me: {app}"
        else:
            system.kill_process(app)
            return f"Successfully closed app not opened by me: {app}"
    except Exception:
        return f"Failed to close {app}"

@beta_tool
def set_volume(volume: float):
    """Set the system volume to a specific level.
    Args:
        volume: The volume level to set (0-100)
    Returns:
        Confirmation that the volume was changed
    """
    try:
        if system.os == "linux":
            system.set_volume_linux(volume)
        elif system.os == "win32":
            system.set_volume_windows(volume)
        return f"Successfully changed volume to {volume}"
    except Exception:
        return f"Failed to change to {volume}"

@beta_tool
def adjust_volume(volume: float):
    """Adjust the system volume up or down by a relative amount.
    Args:
        volume: The amount to adjust the volume by, positive to increase, negative to decrease
    Returns:
        Confirmation that the volume was adjusted
    """
    try:
        if system.os == "linux":
            system.adjust_volume_linux(volume)
        elif system.os == "win32":
            system.adjust_volume_windows(volume)
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
        if system.os == "linux":
            system.mute_linux()
        elif system.os == "win32":
            system.mute_windows()
        else:
            return f"Failed due to os issue {system.os}"
        return "Successfully toggled mute"
    except Exception:
        return "Failed to mute"

@beta_tool
def read_active_file() -> str:
    """Read the currently active file open in the IDE.
    Returns:
        The file path and contents of the active file
    """
    try:
        path = os.path.join(os.environ.get("TEMP", "/tmp"), "jarvis_active_file") if system.os == "win32" else "/tmp/jarvis_active_file"
        return open(path).read()
    except FileNotFoundError:
        return "No file currently open in IDE"

@beta_tool
def jarvis_clip_that(filename: str):
    """
    Clip tha last 30 seconds that occured on screen
    Args:
        filename: The name of the file to clip

    Returns:
        A file in the directory of the last 30 seconds named whatever filename is

    """
    try:
        system.jarvis_clip_that(filename)
        return f"Successfully screenrecord the last 30 sec and saved it to {filename}"
    except Exception as e:
        return f"Failed to screenrecord the last 30 sec: {e}"

def get_size(bytes, suffix="B" ):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

@beta_tool
def get_system_status() -> str:
    """Get the system status as a string.
    Returns:
        The system status as a string
    """
    cpu_freq = psutil.cpu_freq()
    svmem = psutil.virtual_memory()
    disk = psutil.disk_partitions()
    net_io = psutil.net_if_addrs()
    gpus = GPUtil.getGPUs()

    gpu_info = "\n".join([
        f"  {g.name}: {g.load * 100:.1f}% load, {g.memoryUsed}MB/{g.memoryTotal}MB VRAM, {g.temperature}°C"
        for g in gpus
    ]) or "  No GPUs found"

    partition_data = []
    for partition in disk:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partition_data.append(
                f"  {partition.device} ({partition.mountpoint}): {get_size(usage.used)}/{get_size(usage.total)} ({usage.percent}%)"
            )
        except PermissionError:
            continue

    disk_info = "\n".join(partition_data)

    net_data = []
    for interface_name, interface_address in net_io.items():
        for address in interface_address:
            net_data.append(
            f"  {address}: {interface_name}: {address.address}, {address.netmask}, {address.broadcast}")

    net_info = "\n".join(net_data)

    net_speed = network_speed()

    return f"""CPU: {psutil.cpu_count(logical=False)} cores, {cpu_freq.current:.0f}MHz, {psutil.cpu_percent()}% usage
    Memory: {get_size(svmem.used)}/{get_size(svmem.total)} ({svmem.percent}%)
    Disk:
    {disk_info}
    Network: 
    {net_info}
    Network speed:
    {net_speed}
    GPU:
    {gpu_info}
    """


@beta_tool
def network_speed():
    """Get the network speed of the system.
    Returns:
    """
    try:
        io = psutil.net_io_counters()
        bytes_sent, bytes_recv = io.bytes_sent, io.bytes_recv
        time.sleep(1)
        io_2 = psutil.net_io_counters()
        us, ds = io_2.bytes_sent - bytes_sent, io_2.bytes_recv - bytes_recv
        return (f"Upload: {get_size(io_2.bytes_sent)}   "
          f", Download: {get_size(io_2.bytes_recv)}   "
          f", Upload Speed: {get_size(us / 1)}/s   "
          f", Download Speed: {get_size(ds / 1)}/s      ")
    except Exception as e:
        return f"Failed to get network speed: {e}"


def stop_recording():
    """Stop recording the last 30 seconds.
    Returns:
    """
    try:
        system.stop_recording()
        return f"Successfully stop recording"
    except Exception as e:
        return f"Failed to stop recording: {e}"

@beta_tool
def close_all_except(keep: list[str]):
    """
        Close all apps except the ones in keep
    Args:
        keep: apps to keep open

    Returns: Confirmation of whether it was successful or not

    """
    try:
        system.close_all_except(keep)
        return f"Successfully close all apps: {keep}"
    except Exception as e:
        return f"Failed to close all apps: {e}"







