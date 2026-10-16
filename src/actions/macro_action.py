"""
Comando de Multi-Ação / Sequência de Macros.
Executa rotinas encadeadas com suporte a passos de atraso (delays reais).
"""

import time
from typing import Optional, Any
from .base import ActionCommand
from models.action import ActionModel


class MacroCommand(ActionCommand):
    """Executa sequência encadeada de passos de macro."""

    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        from .registry import ActionRegistry

        steps = action.steps
        if not steps:
            return False

        for i, step_dict in enumerate(steps):
            try:
                # Converte passo em ActionModel
                step_model = ActionModel.from_dict(step_dict)
                if not step_model:
                    continue

                if step_model.type == "delay" or "delay" in step_model.raw:
                    d_ms = float(step_model.raw.get("delay", 500))
                    time.sleep(d_ms / 1000.0)
                    continue

                ActionRegistry.dispatch(step_model, slot=slot, engine=engine)

                # Se houver delay configurado no passo
                if step_model.delay > 0:
                    time.sleep(step_model.delay / 1000.0)
                elif i < len(steps) - 1:
                    time.sleep(0.08)  # Intervalo de segurança padrão
            except Exception as e:
                print(f"[MacroCommand] Erro no passo {i}: {e}")

        return True
