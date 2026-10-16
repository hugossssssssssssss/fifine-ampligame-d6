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
