#!/usr/bin/env python3
"""
Validação e Testes Automatizados da Nova Arquitetura Modular do Fifine AmpliGame D6.
Testa:
1. Modelos Tipados (models/)
2. Persistência Atômica & Backup (models/storage.py)
3. Despachante Command Pattern O(1) (actions/)
4. Servidor REST Modular (server/)
"""

import sys
import json
import tempfile
from pathlib import Path

# Adiciona src e sdk ao path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
SDK_DIR = ROOT_DIR / "sdk"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(SDK_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_DIR))

from models.action import ActionModel
from models.key import KeyModel, KeyVisualModel
from models.scene import SceneModel
from models.config import ConfigModel, SettingsModel
from models.storage import StorageManager
from actions.registry import ActionRegistry
from server import create_app_router


def test_models():
    print("[1/4] Testando Modelos de Dados Tipados...")
    action = ActionModel(type="open_app", target="Calculator")
    assert action.type == "open_app"
    assert action.target == "Calculator"

    key = KeyModel(
        slot=1,
        visual=KeyVisualModel(title="CALC", bg="#1e1e2e", accent="#3b82f6"),
        action=action
    )
    assert key.visual.title == "CALC"
    assert key.action.target == "Calculator"

    scene = SceneModel(id="test_scene", name="Test Scene", keys={1: key})
    assert scene.name == "Test Scene"
    assert scene.keys[1].visual.title == "CALC"

    config = ConfigModel(active_page="test", settings=SettingsModel(brightness=90), pages={"test": scene})
    d = config.to_dict()
    assert d["active_page"] == "test"
    assert d["brightness"] == 90
    assert "test" in d["pages"]
    print("  ✓ Modelos tipados e serialização validados com sucesso!")


def test_storage_atomic():
    print("[2/4] Testando Persistência Atômica e Backups...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_cfg_path = Path(tmpdir) / "test_profiles.json"

        cena1 = SceneModel(id="cena1", name="Cena 1")
        cfg = ConfigModel(active_page="cena1", settings=SettingsModel(brightness=75), pages={"cena1": cena1})
        ok = StorageManager.save_atomic(cfg, tmp_cfg_path)
        assert ok, "save_atomic deve retornar True"
        assert tmp_cfg_path.exists(), "Arquivo salvo deve existir"

        loaded = StorageManager.load(tmp_cfg_path)
        assert loaded.active_page == "cena1"
        assert loaded.settings.brightness == 75

        # Testa criação de backup na segunda gravação
        cfg.settings.brightness = 100
        ok2 = StorageManager.save_atomic(cfg, tmp_cfg_path)
        assert ok2
        bak_file = tmp_cfg_path.with_suffix(".json.bak")
        assert bak_file.exists(), "Backup .json.bak deve ter sido gerado"
        with open(bak_file, "r") as f:
            bak_data = json.load(f)
            assert bak_data["brightness"] == 75, "Backup deve manter versão anterior"

        print("  ✓ Persistência atômica e backup validada com sucesso!")


def test_action_registry():
    print("[3/4] Testando Despachante Command Pattern...")
    assert len(ActionRegistry._commands) >= 70, f"Deve haver comandos registrados (total: {len(ActionRegistry._commands)})"

    # Testa resolução O(1) de comandos comuns
    cmd_open = ActionRegistry.resolve("open_app")
    assert cmd_open is not None, "Deve resolver open_app"

    cmd_hotkey = ActionRegistry.resolve("hotkey")
    assert cmd_hotkey is not None, "Deve resolver hotkey"

    cmd_vol = ActionRegistry.resolve("volumeup")
    assert cmd_vol is not None, "Deve resolver volumeup"

    cmd_obs = ActionRegistry.resolve("obsstudio.record")
    assert cmd_obs is not None, "Deve resolver obsstudio.*"

    print(f"  ✓ Despacho Command Pattern validado com {len(ActionRegistry._commands)} manipuladores!")


def test_server_router():
    print("[4/4] Testando Roteador REST Modular...")
    router = create_app_router()
    assert "/api/state" in router._get_routes, "GET /api/state deve estar registrado"
    assert "/api/connect" in router._get_routes, "GET /api/connect deve estar registrado"
    assert "/api/key/update" in router._post_routes, "POST /api/key/update deve estar registrado"
    assert "/api/page/select" in router._post_routes, "POST /api/page/select deve estar registrado"
    assert "/api/obs/status" in router._get_routes, "GET /api/obs/status deve estar registrado"
    assert "/api/backup/export" in router._get_routes, "GET /api/backup/export deve estar registrado"
    print(f"  ✓ Roteador REST validado: {len(router._get_routes)} rotas GET e {len(router._post_routes)} rotas POST registradas!")


if __name__ == "__main__":
    print("\n=======================================================")
    print("  Iniciando Suíte de Testes da Nova Arquitetura")
    print("=======================================================\n")
    test_models()
    test_storage_atomic()
    test_action_registry()
    test_server_router()
    print("\n=======================================================")
    print("  ✓ TODOS OS TESTES PASSARAM COM SUCESSO (100% OK)!")
    print("=======================================================\n")
