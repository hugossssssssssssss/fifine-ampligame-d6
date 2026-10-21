"""
Comandos de Multimídia e Volume para macOS.
Controla volume físico do sistema, mudo e reprodução de faixas.
"""

import subprocess
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class VolumeUpCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        cmd = 'set volume output volume ((output volume of (get volume settings)) + 6.25)'
        subprocess.run(["osascript", "-e", cmd], timeout=2)
        return True


class VolumeDownCommand(ActionCommand):
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        cmd = 'set volume output volume ((output volume of (get volume settings)) - 6.25)'
        subprocess.run(["osascript", "-e", cmd], timeout=2)
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
                new_title = "Caixa"
                new_sub = "Alto-falante"
                new_accent = "#f59e0b"
            else:
                target = "fone bom"
                new_title = "Fone"
                new_sub = "Bluetooth"
                new_accent = "#38bdf8"

            subprocess.run(["/opt/homebrew/bin/SwitchAudioSource", "-s", target], timeout=2)

            if engine and slot:
                page_id = engine.config.get("active_page", "principal")
                k_data = engine.config.get("pages", {}).get(page_id, {}).get("keys", {}).get(str(slot))
                if k_data:
                    k_data["title"] = new_title
                    k_data["subtitle"] = new_sub
                    k_data["accent"] = new_accent
                    engine.sync_key(slot, force=True, page_id=page_id)
            return True
        except Exception as e:
            print(f"[ToggleAudioOutput Error] {e}")
            return False


class SmartPlayPauseCommand(ActionCommand):
    """Play/Pause inteligente: alterna música ou abre YouTube Music no Safari em modo aleatório."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        # 1. Verifica se Spotify está aberto
        try:
            ps_out = subprocess.check_output(["ps", "-A", "-o", "comm"], timeout=1).decode()
        except Exception:
            ps_out = ""

        if "Spotify" in ps_out:
            try:
                state = subprocess.check_output(["osascript", "-e", 'tell application "Spotify" to get player state'], timeout=1).decode().strip()
                if state in ("playing", "paused"):
                    subprocess.run(["osascript", "-e", 'tell application "Spotify" to playpause'], timeout=1)
                    return True
            except Exception:
                pass

        if "Music.app" in ps_out:
            try:
                state = subprocess.check_output(["osascript", "-e", 'tell application "Music" to get player state'], timeout=1).decode().strip()
                if state in ("playing", "paused"):
                    subprocess.run(["osascript", "-e", 'tell application "Music" to playpause'], timeout=1)
                    return True
            except Exception:
                pass

        # 2. Envia tecla multimídia padrão do macOS
        try:
            subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 100'], timeout=1)
        except Exception:
            pass

        # 3. Se Safari não estiver rodando com YouTube Music, abre direto no modo de reprodução
        if "Safari" not in ps_out:
            subprocess.Popen(["open", "-a", "Safari", "https://music.youtube.com"])
        return True

