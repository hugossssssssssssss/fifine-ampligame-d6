"""
Comandos de Multimídia e Volume para macOS.
Controla volume físico do sistema, mudo e reprodução de faixas.
"""

import subprocess
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


def _sync_volume_display(engine: Any, new_vol_str: str):
    """Immediately updates the system volume key display on the active page without delay."""
    if not engine:
        return
    try:
        page_id = engine.config.get("active_page", "principal")
        page = engine.config.get("pages", {}).get(page_id, {})
        for k_str, k_data in page.get("keys", {}).items():
            act = k_data.get("action", {})
            if isinstance(act, dict) and act.get("type") in ("system_stats", "systemstats"):
                if str(act.get("target", "")).lower() in ("volume", "vol", "audio"):
                    if k_data.get("subtitle") != new_vol_str:
                        k_data["subtitle"] = new_vol_str
                        engine.sync_key(int(k_str), force=True, page_id=page_id)
    except Exception as e:
        print(f"[Volume Sync Error] {e}")


class VolumeUpCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        script = 'set volume output volume ((output volume of (get volume settings)) + 6.25)\noutput volume of (get volume settings)'
        try:
            out = subprocess.check_output(["osascript", "-e", script], timeout=2).decode().strip()
            new_vol = f"{int(float(out))}%"
            _sync_volume_display(engine, new_vol)
        except Exception:
            subprocess.run(["osascript", "-e", 'set volume output volume ((output volume of (get volume settings)) + 6.25)'], timeout=2)
        return True


class VolumeDownCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        script = 'set volume output volume ((output volume of (get volume settings)) - 6.25)\noutput volume of (get volume settings)'
        try:
            out = subprocess.check_output(["osascript", "-e", script], timeout=2).decode().strip()
            new_vol = f"{int(float(out))}%"
            _sync_volume_display(engine, new_vol)
        except Exception:
            subprocess.run(["osascript", "-e", 'set volume output volume ((output volume of (get volume settings)) - 6.25)'], timeout=2)
        return True


class MuteCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        cmd = 'set volume output muted not (output muted of (get volume settings))'
        subprocess.run(["osascript", "-e", cmd], timeout=2)
        return True


class PlayPauseCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        # Key code 100 é o play/pause de mídia do macOS
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 100'], timeout=2)
        return True


class NextTrackCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 101'], timeout=2)
        return True


class PrevTrackCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 98'], timeout=2)
        return True


class StopMusicCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        subprocess.run(["osascript", "-e", 'tell application "Music" to pause'], timeout=2)
        return True


class ToggleAudioOutputCommand(ActionCommand):
    """Alterna saída de áudio entre fone Bluetooth e alto-falantes internos do Mac."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        try:
            curr = subprocess.check_output(["/opt/homebrew/bin/SwitchAudioSource", "-c"], timeout=1).decode().strip()
            if "fone" in curr.lower():
                target = "Alto-falantes (Mac mini)"
                new_title = "CAIXA"
                new_sub = ""
                new_accent = "#f59e0b"
                new_icon = "speaker"
            else:
                target = "fone bom"
                new_title = "FONE"
                new_sub = ""
                new_accent = "#38bdf8"
                new_icon = "headphones"

            subprocess.run(["/opt/homebrew/bin/SwitchAudioSource", "-s", target], timeout=2)

            if engine and slot:
                page_id = engine.config.get("active_page", "principal")
                k_data = engine.config.get("pages", {}).get(page_id, {}).get("keys", {}).get(str(slot))
                if k_data:
                    k_data["title"] = new_title
                    k_data["subtitle"] = new_sub
                    k_data["accent"] = new_accent
                    k_data["icon"] = new_icon
                    engine.sync_key(slot, force=True, page_id=page_id)
            return True
        except Exception as e:
            print(f"[ToggleAudioOutput Error] {e}")
            return False


class SmartPlayPauseCommand(ActionCommand):
    """Play/Pause inteligente: alterna música ou abre YouTube Music no Safari em modo aleatório."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        try:
            ps_out = subprocess.check_output(["ps", "-A", "-o", "comm"], timeout=1).decode()
        except Exception:
            ps_out = ""

        # 1. Se Spotify estiver rodando
        if "Spotify" in ps_out:
            try:
                state = subprocess.check_output(["osascript", "-e", 'tell application "Spotify" to get player state'], timeout=1).decode().strip()
                if state in ("playing", "paused"):
                    subprocess.run(["osascript", "-e", 'tell application "Spotify" to playpause'], timeout=1)
                    return True
            except Exception:
                pass

        # 2. Se Apple Music estiver rodando
        if "Music.app" in ps_out:
            try:
                state = subprocess.check_output(["osascript", "-e", 'tell application "Music" to get player state'], timeout=1).decode().strip()
                if state in ("playing", "paused"):
                    subprocess.run(["osascript", "-e", 'tell application "Music" to playpause'], timeout=1)
                    return True
            except Exception:
                pass

        # 3. Verifica se o YouTube Music já está aberto em alguma aba do Safari
        yt_script = '''
tell application "Safari"
    set found to false
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains "music.youtube.com" then
                set current tab of w to t
                set index of w to 1
                set found to true
                exit repeat
            end if
        end repeat
        if found then exit repeat
    end repeat
    if found then
        activate
        tell application "System Events"
            key code 49
        end tell
        return "toggled"
    end if
    return "not_found"
end tell
'''
        try:
            res = subprocess.check_output(["osascript", "-e", yt_script], timeout=2).decode().strip()
            if res == "toggled":
                return True
        except Exception:
            pass

        # 4. Se não estiver tocando nada nem aberto, abre o YouTube Music no Safari no modo aleatório (My Supermix RDMM)
        subprocess.Popen(["open", "-a", "Safari", "https://music.youtube.com/watch?list=RDMM"])
        return True

