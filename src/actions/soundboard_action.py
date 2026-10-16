"""
Comandos de Soundboard e Reprodução de Áudio Local via afplay.
"""

import os
import subprocess
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class SoundboardPlayCommand(ActionCommand):
    """Reproduz arquivo de áudio via afplay em processo independente."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        sound_path = action.path or action.target or ""
        if not sound_path or not os.path.exists(sound_path):
            print(f"[SoundboardPlayCommand] Arquivo de áudio não encontrado: '{sound_path}'")
            return False

        try:
            proc = subprocess.Popen(["afplay", sound_path])
            if engine and hasattr(engine, "_audio_processes"):
                engine._audio_processes = [p for p in engine._audio_processes if p.poll() is None]
                engine._audio_processes.append(proc)
            print(f"[SoundboardPlayCommand] Reproduzindo: '{sound_path}'")
            return True
        except Exception as e:
            print(f"[SoundboardPlayCommand] Erro ao reproduzir áudio: {e}")
            return False


class SoundboardStopCommand(ActionCommand):
    """Interrompe todas as reproduções de áudio ativas."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        if engine and hasattr(engine, "_audio_processes"):
            for proc in engine._audio_processes:
                try:
                    if proc.poll() is None:
                        proc.terminate()
                except Exception:
                    pass
            engine._audio_processes = []
            print("[SoundboardStopCommand] Todos os áudios interrompidos.")
            return True
        return False
