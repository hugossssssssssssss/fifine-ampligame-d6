"""
Comandos de Multimídia e Volume para macOS.
Controla volume físico do sistema, mudo e reprodução de faixas.
"""

import os
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


def _get_volume_step(action: ActionModel, engine: Any) -> float:
    """Resolves volume step increment from action configuration or global engine preferences."""
    raw = getattr(action, "raw", {}) or {}
    if "step" in raw and raw["step"] is not None:
        try:
            return float(raw["step"])
        except (ValueError, TypeError):
            pass
    if engine and hasattr(engine, "config") and "volume_step" in engine.config:
        try:
            return float(engine.config["volume_step"])
        except (ValueError, TypeError):
            pass
    return 6.25


class VolumeUpCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        step = _get_volume_step(action, engine)
        script = f'set volume output volume ((output volume of (get volume settings)) + {step})\noutput volume of (get volume settings)'
        try:
            out = subprocess.check_output(["osascript", "-e", script], timeout=2).decode().strip()
            new_vol = f"{int(float(out))}%"
            _sync_volume_display(engine, new_vol)
        except Exception:
            subprocess.run(["osascript", "-e", f'set volume output volume ((output volume of (get volume settings)) + {step})'], timeout=2)
        return True


class VolumeDownCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        step = _get_volume_step(action, engine)
        script = f'set volume output volume ((output volume of (get volume settings)) - {step})\noutput volume of (get volume settings)'
        try:
            out = subprocess.check_output(["osascript", "-e", script], timeout=2).decode().strip()
            new_vol = f"{int(float(out))}%"
            _sync_volume_display(engine, new_vol)
        except Exception:
            subprocess.run(["osascript", "-e", f'set volume output volume ((output volume of (get volume settings)) - {step})'], timeout=2)
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
    """Alterna saída de áudio entre dois dispositivos selecionados (ex: fone Bluetooth e alto-falantes internos)."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        try:
            bin_path = "/opt/homebrew/bin/SwitchAudioSource"
            if not os.path.exists(bin_path):
                bin_path = "SwitchAudioSource"

            curr = subprocess.check_output([bin_path, "-c"], timeout=1).decode().strip()

            raw = getattr(action, "raw", {}) or {}
            device_a = raw.get("device_a") or (engine.config.get("audio_device_a") if engine else None) or "Alto-falantes (Mac mini)"
            device_b = raw.get("device_b") or (engine.config.get("audio_device_b") if engine else None) or "fone bom"

            # Se o dispositivo atual corresponder ao device_b, alterna para device_a; senão para device_b
            if curr.strip().lower() == device_b.strip().lower() or (len(device_b) > 3 and device_b.strip().lower() in curr.strip().lower()):
                target = device_a
                is_device_b = False
            else:
                target = device_b
                is_device_b = True

            subprocess.run([bin_path, "-s", target], timeout=2)

            if engine and slot:
                page_id = engine.config.get("active_page", "principal")
                k_data = engine.config.get("pages", {}).get(page_id, {}).get("keys", {}).get(str(slot))
                if k_data:
                    if is_device_b:
                        k_data["title"] = "FONE" if any(w in target.lower() for w in ("fone", "headphone", "airpod", "buds", "headset")) else target[:8].upper()
                        k_data["accent"] = "#38bdf8"
                        k_data["icon"] = "headphones"
                    else:
                        k_data["title"] = "CAIXA" if any(w in target.lower() for w in ("alto-falante", "speaker", "fhd", "caixa")) else target[:8].upper()
                        k_data["accent"] = "#f59e0b"
                        k_data["icon"] = "speaker"
                    engine.sync_key(slot, force=True, page_id=page_id)
            return True
        except Exception as e:
            print(f"[ToggleAudioOutput Error] {e}")
            return False


class SmartPlayPauseCommand(ActionCommand):
    """Play/Pause inteligente: alterna música ou abre YouTube Music no Safari com fallback customizável."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        raw = getattr(action, "raw", {}) or {}
        fallback_url = raw.get("fallback_url") or "https://music.youtube.com/watch?list=RDMM"
        auto_shuffle = raw.get("auto_shuffle", True)

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

        # 3. Verifica se o YouTube Music ou serviço de streaming já está aberto no Safari
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

        # 4. Se não estiver tocando nada nem aberto, abre a URL configurada no Safari
        target_url = fallback_url
        if auto_shuffle and "list=RDMM" not in target_url and "music.youtube.com" in target_url:
            separator = "&" if "?" in target_url else "?"
            target_url = f"{target_url}{separator}list=RDMM"

        subprocess.Popen(["open", "-a", "Safari", target_url])
        return True


