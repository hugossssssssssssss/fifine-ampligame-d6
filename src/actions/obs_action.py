"""
Comandos de Integração com OBS Studio WebSocket v5.
Controla gravação, streaming, câmera virtual, modo estúdio, troca de cenas e mixer.
"""

from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class OBSActionCommand(ActionCommand):
    """Comando unificado para acionamento de eventos no OBS Studio."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        if not engine or not hasattr(engine, "obs"):
            return False

        obs = engine.obs
        if not obs.connected:
            obs.connect()

        act_type = (action.uuid or action.type or "").lower()
        sub = act_type.split(".")[-1]

        try:
            if "record" in sub:
                obs.toggle_record()
            elif sub == "stream" or "obs_stream" in act_type:
                obs.toggle_stream()
            elif "virtualcamera" in sub or "virtualcam" in sub:
                obs.toggle_virtualcam()
            elif "studiomode" in sub:
                obs.toggle_studio_mode()
            elif "scene" in sub:
                sc = action.sceneName or action.target or ""
                if sc:
                    obs.set_current_scene(sc)
            elif "mixeraudio" in sub or "audio" in sub or "mute" in sub:
                inp = action.sourceName or action.target or ""
                if inp:
                    obs.toggle_audio_mute(inp)
            elif "source" in sub:
                sc = action.sceneName or obs.current_scene
                item_id = action.sceneItemId
                vis = action.visible
                if sc and item_id:
                    obs.set_source_visibility(sc, int(item_id), vis)
            elif "screenshot" in sub:
                sc = action.sceneName or ""
                obs.trigger_screenshot(sc)

            return True
        except Exception as e:
            print(f"[OBSActionCommand] Erro ao executar ação OBS: {e}")
            return False
