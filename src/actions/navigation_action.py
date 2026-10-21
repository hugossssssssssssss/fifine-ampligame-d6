"""
Comandos de Navegação entre Cenas, Páginas e Pastas.
Gerencia transições no StreamDeck e atualização instantânea de hardware.
"""

from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class NavigationCommand(ActionCommand):
    """Comando polimórfico para troca de página, abertura de pasta ou retorno ao pai."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        if not engine:
            return False

        act_type = action.type.lower()
        tgt = action.target or action.raw.get("page") or action.raw.get("pageAction") or action.raw.get("folder_id") or ""

        # 1. Abrir pasta filha
        if "openchild" in act_type or act_type == "folder":
            if tgt and tgt in engine.config.get("pages", {}):
                engine.change_page(tgt)
                return True

        # 2. Voltar ao nível pai
        if "backtoparent" in act_type:
            cur_page = engine.config.get("active_page", "principal")
            parent = tgt or engine.config.get("pages", {}).get(cur_page, {}).get("parent_page", "principal")
            if parent in engine.config.get("pages", {}):
                engine.change_page(parent)
                return True

        # 3. Próxima / Anterior / Rotação
        keys = list(engine.config.get("pages", {}).keys())
        if not keys:
            return False

        cur_idx = keys.index(engine.config.get("active_page", "principal")) if engine.config.get("active_page") in keys else 0

        if tgt == "next" or "rotate" in act_type or "page.next" in act_type or action.uuid.endswith(".next"):
            tgt = keys[(cur_idx + 1) % len(keys)]
        elif tgt == "previous" or "page.previous" in act_type or action.uuid.endswith(".previous"):
            tgt = keys[(cur_idx - 1) % len(keys)]
        elif "goto" in act_type or action.uuid.endswith(".goto"):
            if tgt and tgt in engine.config.get("pages", {}):
                engine.change_page(tgt)
                return True
        elif "indicator" in act_type or action.uuid.endswith(".indicator"):
            # Informational indicator - refresh keys
            engine.sync_all_keys()
            return True

        if tgt and tgt in engine.config.get("pages", {}):
            engine.change_page(tgt)
            return True

        return False
