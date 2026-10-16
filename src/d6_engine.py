#!/usr/bin/env python3
"""
Fifine AmpliGame D6 Engine & Profile Manager
Controla o hardware físico, gerencia páginas de botões, renderiza teclas com Pillow
e despacha ações de sistema, automações, mídia e TV.
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional

# Adiciona o SDK local
SDK_PATH = Path(__file__).resolve().parent.parent / "streamdock-sdk" / "Python-SDK" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

import ctypes
import ctypes.util

_cg = None
_cf = None
_libsys = None

try:
    _cg_path = ctypes.util.find_library("CoreGraphics")
    if _cg_path:
        _cg = ctypes.cdll.LoadLibrary(_cg_path)
        _cg.CGMainDisplayID.restype = ctypes.c_uint32
        _cg.CGDisplayIsAsleep.restype = ctypes.c_int
        _cg.CGDisplayIsAsleep.argtypes = [ctypes.c_uint32]
        _cg.CGSessionCopyCurrentDictionary.restype = ctypes.c_void_p

    _cf_path = ctypes.util.find_library("CoreFoundation")
    if _cf_path:
        _cf = ctypes.cdll.LoadLibrary(_cf_path)
        _cf.CFDictionaryGetValue.restype = ctypes.c_void_p
        _cf.CFDictionaryGetValue.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        _cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        _cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        _cf.CFBooleanGetValue.restype = ctypes.c_bool
        _cf.CFBooleanGetValue.argtypes = [ctypes.c_void_p]
        _cf.CFRelease.argtypes = [ctypes.c_void_p]

    _libsys = ctypes.cdll.LoadLibrary("/usr/lib/libSystem.B.dylib")
    _libsys.notify_register_check.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    _libsys.notify_register_check.restype = ctypes.c_int
    _libsys.notify_get_state.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint64)]
    _libsys.notify_get_state.restype = ctypes.c_int
    _libsys.notify_cancel.argtypes = [ctypes.c_int]
    _libsys.notify_cancel.restype = ctypes.c_int
except Exception as e:
    print(f"[Engine] Aviso: Falha ao carregar bibliotecas macOS para detecção de display sleep: {e}")

from PIL import Image, ImageDraw, ImageFont

try:
    from StreamDock.DeviceManager import DeviceManager
    from StreamDock.Devices.StreamDock293s import StreamDock293s
    from StreamDock.ImageHelpers.PILHelper import to_native_key_format
except ImportError:
    DeviceManager = None
    StreamDock293s = None
    to_native_key_format = None

from obs_client import OBSClient
from models.storage import StorageManager
from actions.registry import ActionRegistry

PROFILES_FILE = Path(__file__).resolve().parent / "d6_profiles.json"
ICONS_DIR = Path(__file__).resolve().parent / "studio" / "icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)


DEFAULT_PROFILES = {
    "active_page": "principal",
    "brightness": 80,
    "led_sleep_follow": True,
    "screen_off_seconds": 0,
    "rotation": 0,
    "pages": {
        "principal": {
            "name": "Principal & Workspace",
            "keys": {
                "1": {
                    "title": "SLIDES",
                    "subtitle": "Google",
                    "bg": "#1e1e2e",
                    "textColor": "#ffffff",
                    "accent": "#f59e0b",
                    "fontSize": 15,
                    "icon": "presentation",
                    "action": {"type": "open_url", "url": "https://slides.google.com"}
                },
                "2": {
                    "title": "DOCS",
                    "subtitle": "Google",
                    "bg": "#1e1e2e",
                    "textColor": "#ffffff",
                    "accent": "#3b82f6",
                    "fontSize": 15,
                    "icon": "file-text",
                    "action": {"type": "open_url", "url": "https://docs.google.com"}
                },
                "3": {
                    "title": "SHEETS",
                    "subtitle": "Google",
                    "bg": "#1e1e2e",
                    "textColor": "#ffffff",
                    "accent": "#10b981",
                    "fontSize": 15,
                    "icon": "table",
                    "action": {"type": "open_url", "url": "https://sheets.google.com"}
                },
                "4": {
                    "title": "DRIVE",
                    "subtitle": "Google",
                    "bg": "#1e1e2e",
                    "textColor": "#ffffff",
                    "accent": "#8b5cf6",
                    "fontSize": 15,
                    "icon": "hard-drive",
                    "action": {"type": "open_url", "url": "https://drive.google.com"}
                },
                "5": {
                    "title": "PPTX",
                    "subtitle": "Grade",
                    "bg": "#1e1e2e",
                    "textColor": "#ffffff",
                    "accent": "#ef4444",
                    "fontSize": 15,
                    "icon": "layout-grid",
                    "action": {"type": "shell", "cmd": "echo 'PowerPoint Trigger'"}
                },
                "6": {
                    "title": "TV POWER",
                    "subtitle": "Samsung",
                    "bg": "#18181b",
                    "textColor": "#ffffff",
                    "accent": "#06b6d4",
                    "fontSize": 14,
                    "icon": "tv",
                    "action": {"type": "samsung_tv", "key": "KEY_POWER"}
                },
                "7": {
                    "title": "TV VOL -",
                    "subtitle": "Samsung",
                    "bg": "#18181b",
                    "textColor": "#ffffff",
                    "accent": "#06b6d4",
                    "fontSize": 14,
                    "icon": "volume-1",
                    "action": {"type": "samsung_tv", "key": "KEY_VOLDOWN"}
                },
                "8": {
                    "title": "TV VOL +",
                    "subtitle": "Samsung",
                    "bg": "#18181b",
                    "textColor": "#ffffff",
                    "accent": "#06b6d4",
                    "fontSize": 14,
                    "icon": "volume-2",
                    "action": {"type": "samsung_tv", "key": "KEY_VOLUP"}
                },
                "9": {
                    "title": "TV MUTE",
                    "subtitle": "Samsung",
                    "bg": "#18181b",
                    "textColor": "#ffffff",
                    "accent": "#ec4899",
                    "fontSize": 14,
                    "icon": "volume-x",
                    "action": {"type": "samsung_tv", "key": "KEY_MUTE"}
                },
                "10": {
                    "title": "N8N",
                    "subtitle": "Proxy",
                    "bg": "#18181b",
                    "textColor": "#ffffff",
                    "accent": "#f97316",
                    "fontSize": 15,
                    "icon": "webhook",
                    "action": {"type": "open_url", "url": "http://127.0.0.1:5678"}
                },
                "11": {
                    "title": "CPU",
                    "subtitle": "Live",
                    "bg": "#0f172a",
                    "textColor": "#ffffff",
                    "accent": "#38bdf8",
                    "fontSize": 15,
                    "icon": "cpu",
                    "action": {"type": "system_stats", "target": "cpu"}
                },
                "12": {
                    "title": "RAM",
                    "subtitle": "Live",
                    "bg": "#0f172a",
                    "textColor": "#ffffff",
                    "accent": "#a855f7",
                    "fontSize": 15,
                    "icon": "activity",
                    "action": {"type": "system_stats", "target": "ram"}
                },
                "13": {
                    "title": "MIC",
                    "subtitle": "Mac",
                    "bg": "#14532d",
                    "textColor": "#ffffff",
                    "accent": "#22c55e",
                    "fontSize": 15,
                    "icon": "mic",
                    "action": {"type": "mic_toggle"}
                },
                "14": {
                    "title": "BRILHO -",
                    "subtitle": "Deck",
                    "bg": "#27272a",
                    "textColor": "#ffffff",
                    "accent": "#71717a",
                    "fontSize": 14,
                    "icon": "sun",
                    "action": {"type": "brightness", "step": -20}
                },
                "15": {
                    "title": "BRILHO +",
                    "subtitle": "Deck",
                    "bg": "#27272a",
                    "textColor": "#ffffff",
                    "accent": "#e4e4e7",
                    "fontSize": 14,
                    "icon": "sun",
                    "action": {"type": "brightness", "step": 20}
                }
            }
        },
        "streaming": {
            "name": "Streaming & OBS",
            "keys": {
                "1": {"title": "OBS", "subtitle": "Abrir", "bg": "#1e1e2e", "accent": "#3b82f6", "action": {"type": "open_app", "app": "OBS"}},
                "2": {"title": "CENA 1", "subtitle": "Câmera", "bg": "#18181b", "accent": "#10b981", "action": {"type": "hotkey", "keys": "F13"}},
                "3": {"title": "CENA 2", "subtitle": "Tela", "bg": "#18181b", "accent": "#10b981", "action": {"type": "hotkey", "keys": "F14"}},
                "4": {"title": "REC", "subtitle": "Gravar", "bg": "#7f1d1d", "accent": "#ef4444", "action": {"type": "hotkey", "keys": "F15"}},
                "5": {"title": "HOME", "subtitle": "Voltar", "bg": "#27272a", "accent": "#6366f1", "action": {"type": "change_page", "page": "principal"}}
            }
        }
    }
}


class D6Engine:
    KEY_SIZE = (96, 96)  # Resolução nativa real do hardware Fifine AmpliGame D6 (revertida via REA do app oficial)

    def __init__(self):
        self.device = None
        self.manager = DeviceManager() if DeviceManager else None
        self.config = self._load_config()
        self.lock = threading.Lock()
        self.running = False
        self._last_mic_state = None
        self._last_stats_update = 0
        self._last_manual_page = self.config.get("active_page", "principal")
        self._auto_switched = False
        self._last_frontmost_app_name = ""
        self._last_app_check_time = 0.0
        self._last_activity_time = time.time()
        self.is_asleep = False
        self._saved_brightness = self.config.get("brightness", 80)
        self._displayed_key_hashes = {}  # Dirty checking de alta velocidade para cada LCD físico
        self._audio_processes = []  # Processos de áudio ativos (Soundboard)
        self._last_pressed_slot = None  # Último slot pressionado no hardware/UI para feedback tátil
        self._last_pressed_ts = 0.0  # Timestamp do último clique para sincronização Web UI

        # 10. Cliente WebSocket Oficial para OBS Studio v5
        obs_cfg = self.config.get("obs", {})
        self.obs = OBSClient(
            host=obs_cfg.get("host", "127.0.0.1"),
            port=obs_cfg.get("port", 4455),
            password=obs_cfg.get("password", ""),
            auto_reconnect=obs_cfg.get("auto_connect", True)
        )
        self.obs.add_state_listener(self._on_obs_state_changed)
        if obs_cfg.get("auto_connect", True):
            self.obs.connect()

    def _on_obs_state_changed(self, client: OBSClient):
        """Atualiza dinamicamente as teclas de ações do OBS na página ativa quando o status do OBS muda."""
        page_id = self.config.get("active_page", "principal")
        page = self.config.get("pages", {}).get(page_id, {})
        keys = page.get("keys", {})

        obs_dir = Path("/Applications/fifine Control Deck.app/Contents/Resources/plugins/com.hotspot.streamdock.obsstudio.sdPlugin/Images/actions")
        for k_str, k_data in list(keys.items()):
            if not isinstance(k_data, dict):
                continue
            act = k_data.get("action")
            if isinstance(act, str):
                act = {"type": act}
            elif not isinstance(act, dict):
                act = {}
            act_type = str(act.get("uuid") or act.get("type") or "").lower()
            if "obsstudio" not in act_type and not act_type.startswith("obs_"):
                continue

            sub = act_type.split(".")[-1]
            updated = False
            # Gravação
            if "record" in sub:
                if client.is_recording:
                    k_data["title"] = "REC ON"
                    k_data["accent"] = "#ef4444"
                    cand = obs_dir / "record" / "on_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                else:
                    k_data["title"] = "REC"
                    k_data["accent"] = "#71717a"
                    cand = obs_dir / "record" / "off_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                updated = True

            # Transmissão / Live (apenas ação real de stream, sem conflito com streamdock)
            elif sub == "stream" or "obs_stream" in act_type:
                if client.is_streaming:
                    k_data["title"] = "AO VIVO"
                    k_data["accent"] = "#10b981"
                    cand = obs_dir / "stream" / "on_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                else:
                    k_data["title"] = "STREAM"
                    k_data["accent"] = "#71717a"
                    cand = obs_dir / "stream" / "off_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                updated = True

            # Cenas do OBS
            elif "scene" in sub:
                target_scene = act.get("scene") or act.get("target") or act.get("name") or act.get("sceneName") or ""
                is_active = bool(target_scene and client.current_scene and target_scene.lower() == client.current_scene.lower())
                if is_active:
                    k_data["accent"] = "#007aff"
                    cand = obs_dir / "scene" / "on_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                else:
                    k_data["accent"] = "#3f3f46"
                    cand = obs_dir / "scene" / "off_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                updated = True

            # Mixer de Áudio
            elif "mixeraudio" in sub or "audio" in sub or "mute" in sub:
                target_audio = act.get("input") or act.get("target") or act.get("source") or act.get("sourceName") or ""
                is_muted = client.audio_inputs.get(target_audio, False)
                if is_muted:
                    k_data["title"] = "MUTED"
                    k_data["accent"] = "#ef4444"
                    cand = obs_dir / "source.audio.mute" / "off_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                else:
                    k_data["title"] = "AUDIO"
                    k_data["accent"] = "#10b981"
                    cand = obs_dir / "source.audio.mute" / "on_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                updated = True

            # Câmera Virtual
            elif "virtualcamera" in sub or "virtualcam" in sub:
                if client.is_virtualcam:
                    k_data["accent"] = "#06b6d4"
                    cand = obs_dir / "virtualcamera" / "on_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                else:
                    k_data["accent"] = "#71717a"
                    cand = obs_dir / "virtualcamera" / "off_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                updated = True

            # Modo Estúdio
            elif "studiomode" in sub:
                if client.is_studiomode:
                    k_data["accent"] = "#a855f7"
                    cand = obs_dir / "studiomode" / "on_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                else:
                    k_data["accent"] = "#71717a"
                    cand = obs_dir / "studiomode" / "off_png.png"
                    if cand.exists():
                        k_data["imagePath"] = str(cand)
                updated = True

            if updated and not getattr(self, "is_asleep", False):
                self.sync_key(int(k_str))

    def _resolve_action_image(self, p_dir: Path, uuid: str, img_name: str) -> str:
        """Resolve o caminho da imagem de uma ação nativa do Fifine."""
        if "obsstudio" in uuid:
            sub = uuid.split(".")[-1]
            if sub == "mixeraudio":
                sub = "source.audio.mute"
            obs_actions = Path("/Applications/fifine Control Deck.app/Contents/Resources/plugins/com.hotspot.streamdock.obsstudio.sdPlugin/Images/actions")
            for cand_name in ["on_png.png", "icon.png", "off_png.png"]:
                c = obs_actions / sub / cand_name
                if c.exists():
                    return str(c)

        if not img_name:
            if "openApps" in uuid:
                plugin_launch = Path("/Applications/fifine Control Deck.app/Contents/Resources/plugins/com.hotspot.streamdock.system.open.sdPlugin/Images/btn_launch.png")
                if plugin_launch.exists():
                    return str(plugin_launch)
            return ""

        # 1. Busca na pasta Images do próprio profile
        local_img = p_dir / "Images" / img_name
        if local_img.exists():
            return str(local_img)

        # 2. Busca na pasta de plugins do aplicativo oficial da Fifine
        app_plugins = Path("/Applications/fifine Control Deck.app/Contents/Resources/plugins")
        plugin_dir = app_plugins / f"{uuid}.sdPlugin" / "Images"
        if plugin_dir.exists():
            base = os.path.basename(img_name)
            for ext in ["", ".png", ".jpg", ".gif", "@2x.png"]:
                cand = plugin_dir / f"{base}{ext}"
                if cand.exists():
                    return str(cand)

        # 3. Busca nas imagens de usuário do Studio
        user_img = Path(__file__).resolve().parent / "studio" / "user_images" / os.path.basename(img_name)
        if user_img.exists():
            return str(user_img)

        return ""

    def _sync_native_fifine_profiles(self, config: Dict[str, Any]):
        """Sincroniza dinamicamente todos os perfis e subpastas da pasta oficial da Fifine."""
        streamdock_profiles = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles"
        if not streamdock_profiles.exists():
            return
        if "pages" not in config:
            config["pages"] = {}

        all_profiles = []
        for p in sorted(streamdock_profiles.glob("*.sdProfile")):
            all_profiles.append((p, None))
            for child in sorted((p / "profiles").glob("*.sdProfile")):
                all_profiles.append((child, p))

        for p_dir, parent_dir in all_profiles:
            m_file = p_dir / "manifest.json"
            if not m_file.exists():
                continue
            try:
                with open(m_file, "r", encoding="utf-8") as mf:
                    m_data = json.load(mf)
                name = m_data.get("Name")
                if not name:
                    if parent_dir:
                        name = "Pasta de Apps"
                    else:
                        name = p_dir.stem

                # Identificador limpo e determinístico
                if parent_dir:
                    key_id = f"pasta_{p_dir.stem[:8].lower()}"
                else:
                    norm = name.lower().replace(" ", "_").replace("ã", "a").replace("á", "a")
                    key_id = "principal" if norm == "cena_padrao" else norm

                if key_id not in config["pages"]:
                    config["pages"][key_id] = {
                        "name": name,
                        "native_folder": p_dir.name,
                        "keys": {}
                    }
                else:
                    config["pages"][key_id]["name"] = name
                    config["pages"][key_id]["native_folder"] = p_dir.name
                    if "keys" not in config["pages"][key_id]:
                        config["pages"][key_id]["keys"] = {}

                # Importa ou atualiza ações contidas no manifest
                actions = m_data.get("Actions", {})
                for coord, act in actions.items():
                    try:
                        x, y = map(int, coord.split(","))
                        slot = str((y * 5) + x + 1)
                    except Exception:
                        continue

                    uuid = act.get("UUID", "")
                    settings = act.get("Settings", {})
                    states = act.get("States", [{}])
                    st0 = states[0] if states else {}
                    title = st0.get("Title", "")
                    img_name = st0.get("Image", "")
                    font_size = int(st0.get("FontSize", 14)) if str(st0.get("FontSize", "")).isdigit() else 14
                    text_color = st0.get("TitleColor", "#ffffff") or "#ffffff"
                    resolved_img = self._resolve_action_image(p_dir, uuid, img_name)

                    # Determina tipo de ação
                    if "openchild" in uuid:
                        target_page = f"pasta_{act.get('Settings', {}).get('ProfileUUID', '')[:8].lower()}"
                        action_def = {"type": "change_page", "target": target_page}
                        if not title:
                            title = "PASTA"
                    elif "backtoparent" in uuid:
                        action_def = {"type": "change_page", "target": "principal"}
                        if not title:
                            title = "VOLTAR"
                    elif "rotate" in uuid:
                        action_def = {"type": "rotate_scenes"}
                    elif "website" in uuid:
                        action_def = {"type": "website", "url": settings.get("path", "")}
                    elif "hotkey" in uuid:
                        action_def = {"type": "hotkey", "keys": settings.get("Hotkeys", "")}
                    elif "text" in uuid:
                        action_def = {"type": "text", "text": settings.get("text", ""), "enter": settings.get("enter", False)}
                    elif "openApps" in uuid:
                        apps = settings.get("applications", [])
                        app_target = apps[0].get("path", "") if apps else ""
                        action_def = {"type": "open", "target": app_target}
                    elif "open" in uuid:
                        action_def = {"type": "open", "target": settings.get("path", "")}
                    else:
                        action_def = {"type": uuid}

                    # Só sobrescreve se o slot não foi explicitamente customizado localmente
                    if slot not in config["pages"][key_id]["keys"] or not config["pages"][key_id]["keys"][slot].get("title"):
                        config["pages"][key_id]["keys"][slot] = {
                            "title": title,
                            "subtitle": "",
                            "fontSize": font_size,
                            "textColor": text_color,
                            "bg": "#18181b",
                            "accent": "#007aff",
                            "imagePath": resolved_img,
                            "action": action_def
                        }
                    else:
                        # Assegura que imagePath esteja atualizado
                        if resolved_img and not config["pages"][key_id]["keys"][slot].get("imagePath"):
                            config["pages"][key_id]["keys"][slot]["imagePath"] = resolved_img

            except Exception as e:
                print(f"[Engine] Erro ao sincronizar profile {p_dir.name}: {e}")

    def sync_with_native_profiles(self):
        """Atualiza a configuração viva com os arquivos nativos no disco."""
        self._sync_native_fifine_profiles(self.config)

    def create_native_profile(self, name: str, page_id: str) -> str:
        """Cria um .sdProfile nativo compatível com o aplicativo oficial da Fifine."""
        import uuid
        profile_uuid = str(uuid.uuid4()).upper()
        folder_name = f"{profile_uuid}.sdProfile"
        streamdock_profiles = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles"
        dest_dir = streamdock_profiles / folder_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "Images").mkdir(exist_ok=True)
        (dest_dir / "profiles").mkdir(exist_ok=True)

        manifest = {
            "Actions": {},
            "DeviceModel": "20GBA9901",
            "DeviceSerialNumber": "355499441494",
            "DeviceUUID": "D6",
            "Name": name,
            "Pages": {
                "Current": folder_name,
                "Pages": [folder_name]
            },
            "Version": "1.0"
        }
        with open(dest_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        return folder_name

    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações via StorageManager com suporte a migração e backup."""
        try:
            config_model = StorageManager.load(PROFILES_FILE)
            cfg = config_model.to_dict()
        except Exception as e:
            print(f"[Engine] Erro ao carregar via StorageManager: {e}")
            cfg = json.loads(json.dumps(DEFAULT_PROFILES))

        self._sync_native_fifine_profiles(cfg)
        return cfg

    def save_config(self):
        """Salva as configurações no disco de forma atômica com backup automático."""
        StorageManager.save_atomic(self.config, PROFILES_FILE)

    def rename_page(self, page_id: str, new_name: str) -> bool:
        """Renomeia a página no arquivo de perfis e atualiza o manifest.json nativo se existir."""
        if page_id not in self.config.get("pages", {}):
            return False
        clean_name = new_name.strip()
        if not clean_name:
            return False
        self.config["pages"][page_id]["name"] = clean_name
        self.save_config()

        # Atualiza o manifest.json nativo
        native_folder = self.config["pages"][page_id].get("native_folder")
        if native_folder:
            m_path = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles" / native_folder / "manifest.json"
            if m_path.exists():
                try:
                    with open(m_path, "r", encoding="utf-8") as f:
                        m_data = json.load(f)
                    m_data["Name"] = clean_name
                    with open(m_path, "w", encoding="utf-8") as f:
                        json.dump(m_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"[Engine] Erro ao atualizar manifest na renomeação: {e}")
        return True

    def duplicate_page(self, page_id: str) -> str:
        """Duplica um perfil existente com todas as suas teclas e cria um .sdProfile nativo."""
        if page_id not in self.config.get("pages", {}):
            return ""
        orig = self.config["pages"][page_id]
        new_name = f"{orig.get('name', page_id)} (Cópia)"
        new_id = f"cena_{int(time.time())}"

        native_folder = self.create_native_profile(new_name, new_id)
        import copy
        self.config["pages"][new_id] = {
            "name": new_name,
            "native_folder": native_folder,
            "keys": copy.deepcopy(orig.get("keys", {}))
        }
        self.save_config()
        return new_id

    def get_icon_packs(self) -> List[Dict[str, Any]]:
        """Lista os pacotes de ícones nativos oficiais da Fifine."""
        icons_dir = Path("/Applications/fifine Control Deck.app/Contents/Resources/icons")
        if not icons_dir.exists():
            return []
        packs = []
        for p_dir in sorted(icons_dir.iterdir()):
            if not p_dir.is_dir():
                continue
            m_file = p_dir / "manifest.json"
            name = p_dir.name
            if m_file.exists():
                try:
                    with open(m_file) as f:
                        name = json.load(f).get("Name", name)
                except Exception:
                    pass
            icons = []
            img_dir = p_dir / "icons"
            if img_dir.exists():
                for f in sorted(img_dir.iterdir()):
                    if f.suffix.lower() in [".jpg", ".png", ".gif", ".svg"]:
                        icons.append({
                            "name": f.stem,
                            "filename": f.name,
                            "path": str(f)
                        })
            packs.append({
                "id": p_dir.name,
                "name": name,
                "count": len(icons),
                "icons": icons
            })
        return packs

    def get_skins(self) -> List[Dict[str, Any]]:
        """Lista as skins e papéis de parede nativos de 15 teclas oficiais da Fifine."""
        skin_dir = Path("/Applications/fifine Control Deck.app/Contents/MacOS/skin")
        if not skin_dir.exists():
            return []
        skins = []
        for s_dir in sorted(skin_dir.iterdir()):
            if not s_dir.is_dir():
                continue
            imgs = sorted([f for f in s_dir.iterdir() if f.suffix.lower() in [".jpg", ".png"]])
            preview = str(imgs[0]) if imgs else ""
            skins.append({
                "id": s_dir.name,
                "name": s_dir.name.replace("-", " ").capitalize(),
                "count": len(imgs),
                "preview": preview
            })
        return skins

    def apply_skin(self, skin_id: str, page_id: str = None) -> bool:
        """Aplica um tema ou papel de parede nativo de 15 teclas ao perfil ativo."""
        target_page = page_id or self.config.get("active_page", "principal")
        if target_page not in self.config.get("pages", {}):
            return False
        skin_path = Path("/Applications/fifine Control Deck.app/Contents/MacOS/skin") / skin_id
        if not skin_path.exists():
            return False

        imgs = sorted([f for f in skin_path.iterdir() if f.suffix.lower() in [".jpg", ".png"]])
        if not imgs:
            return False

        if "keys" not in self.config["pages"][target_page]:
            self.config["pages"][target_page]["keys"] = {}

        # Mapeia as imagens ordenadas para os slots 1 a 15
        for idx in range(15):
            slot = str(idx + 1)
            img_file = imgs[idx % len(imgs)]
            if slot not in self.config["pages"][target_page]["keys"]:
                self.config["pages"][target_page]["keys"][slot] = {
                    "title": "",
                    "subtitle": "",
                    "bg": "#141418",
                    "imagePath": str(img_file),
                    "action": {"type": "none"}
                }
            else:
                self.config["pages"][target_page]["keys"][slot]["imagePath"] = str(img_file)

        self.save_config()
        if target_page == self.config.get("active_page"):
            self.sync_all_keys()
        return True

    def restore_golden_backup(self) -> bool:
        """Restaura todos os perfis e pastas originais protegidos pelo Guardian."""
        backup_dir = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles_golden_backup"
        profiles_dir = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles"
        if not backup_dir.exists():
            return False
        import shutil
        for p in backup_dir.glob("*.sdProfile"):
            dest = profiles_dir / p.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(p, dest)
        self.sync_with_native_profiles()
        self.sync_all_keys()
        return True

    def connect(self) -> bool:
        if not self.manager:
            return False
        devices = self.manager.enumerate()
        if not devices:
            return False
        try:
            self.device = devices[0]
            if not self.device.open():
                self.device = None
                self._is_open = False
                return False
            self.device.set_device()
            self.device.wakeScreen()
            self.set_brightness(self.config.get("brightness", 80))
            self.device.set_key_callback(self._on_hardware_key)
            self._is_open = True
            print("[Engine] AmpliGame D6 conectado e pronto.")
            self._displayed_key_hashes.clear()
            self.sync_all_keys(force=True)
            return True
        except Exception as e:
            print(f"[Engine] Falha ao conectar D6: {e}")
            self.device = None
            self._is_open = False
            return False

    def close(self):
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
        self._is_open = False

    def is_connected(self) -> bool:
        return getattr(self, "_is_open", False) and self.device is not None

    def set_brightness(self, percent: int, save: bool = True):
        percent = max(0, min(100, int(percent)))
        if save:
            self.config["brightness"] = percent
            self._saved_brightness = percent
        if self.device:
            try:
                self.device.set_brightness(percent)
            except Exception as e:
                print(f"[Engine] Erro de brilho: {e}")

    def reset_inactivity(self):
        """Reseta o temporizador de inatividade."""
        self._last_activity_time = time.time()

    def is_mac_screen_off_or_locked(self) -> bool:
        """Verifica se a sessão do macOS está realmente bloqueada ou com protetor de tela ativo (sem falsos positivos de CGDisplayIsAsleep)."""
        # Se houve atividade recente no web studio, o usuário está configurando o deck
        if time.time() - getattr(self, "_last_web_activity_time", 0) < 30:
            return False

        if _cg:
            try:
                s_dict = _cg.CGSessionCopyCurrentDictionary()
                if s_dict:
                    k = _cf.CFStringCreateWithCString(None, b"CGSSessionScreenIsLocked", 0x08000100)
                    val = _cf.CFDictionaryGetValue(s_dict, k)
                    _cf.CFRelease(k)
                    locked = False
                    if val:
                        locked = _cf.CFBooleanGetValue(val)
                    _cf.CFRelease(s_dict)
                    if locked:
                        return True
            except Exception:
                pass

        if _libsys:
            for notif_name in (b"com.apple.screenIsLocked", b"com.apple.screensaver.didstart"):
                try:
                    token = ctypes.c_int()
                    if _libsys.notify_register_check(notif_name, ctypes.byref(token)) == 0:
                        st = ctypes.c_uint64()
                        _libsys.notify_get_state(token.value, ctypes.byref(st))
                        _libsys.notify_cancel(token.value)
                        if st.value != 0:
                            return True
                except Exception:
                    pass

        return False

    def sleep_device(self, reason: str = "Inatividade"):
        """Coloca o hardware em suspensão / proteção contra burn-in (apaga a luz de fundo e limpa LCDs)."""
        if self.is_asleep:
            return
        self.is_asleep = True
        self._saved_brightness = self.config.get("brightness", 80)
        print(f"[Engine] {reason} detectada -> Entrando em modo Sleep / Desligando Telas LCD")
        if self.device:
            try:
                self.device.set_brightness(0)
            except Exception as e:
                print(f"[Engine] Erro ao suspender brilho: {e}")
            try:
                if hasattr(self.device, "transport") and self.device.transport:
                    if hasattr(self.device.transport, "clear_all_keys"):
                        self.device.transport.clear_all_keys()
                    if hasattr(self.device.transport, "sleep"):
                        self.device.transport.sleep()
            except Exception as e:
                print(f"[Engine] Erro ao suspender transporte USB: {e}")

    def wake_device(self, reason: str = "Atividade"):
        """Acorda o hardware da suspensão, acorda display e restaura a iluminação de fundo e teclas."""
        if not self.is_asleep:
            return
        self.is_asleep = False
        self._slept_by_mac_display = False
        target_b = self._saved_brightness or self.config.get("brightness", 80)
        if target_b <= 0:
            target_b = 80
        print(f"[Engine] Acordando Stream Deck ({reason}) -> Restaurando iluminação ({target_b}%) e teclas")
        if self.device:
            try:
                if hasattr(self.device, "wakeScreen"):
                    self.device.wakeScreen()
                elif hasattr(self.device, "transport") and self.device.transport:
                    if hasattr(self.device.transport, "wakeup_screen"):
                        self.device.transport.wakeup_screen()
            except Exception as e:
                print(f"[Engine] Erro ao acordar tela: {e}")
        self.set_brightness(target_b, save=False)
        self.reset_inactivity()
        self.sync_all_keys()

    def get_mac_hid_idle_time(self) -> float:
        """Obtém o tempo de inatividade global do usuário no macOS (em segundos) via IOHIDSystem."""
        try:
            res = subprocess.run(
                ["/bin/sh", "-c", "ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print int($NF/1000000000); exit}'"],
                capture_output=True, text=True, timeout=1
            )
            if res.returncode == 0 and res.stdout.strip():
                return float(res.stdout.strip())
        except Exception:
            pass
        return 0.0

    def render_empty_key_image(self) -> Image.Image:
        """Gera imagem de tecla inativa/vazia completamente preta e limpa (LCD desligado)."""
        return Image.new("RGB", self.KEY_SIZE, color="#000000")

    @staticmethod
    def _resolve_font(family: str = "Helvetica", size: int = 14, bold: bool = False, italic: bool = False) -> ImageFont.ImageFont:
        f_map = {
            "arial": {
                (False, False): "/System/Library/Fonts/Supplemental/Arial.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                (False, True): "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
                (True, True): "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
            },
            "courier new": {
                (False, False): "/System/Library/Fonts/Supplemental/Courier New.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
                (False, True): "/System/Library/Fonts/Supplemental/Courier New Italic.ttf",
                (True, True): "/System/Library/Fonts/Supplemental/Courier New Bold Italic.ttf",
            },
            "georgia": {
                (False, False): "/System/Library/Fonts/Supplemental/Georgia.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                (False, True): "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
                (True, True): "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf",
            },
            "verdana": {
                (False, False): "/System/Library/Fonts/Supplemental/Verdana.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
                (False, True): "/System/Library/Fonts/Supplemental/Verdana Italic.ttf",
                (True, True): "/System/Library/Fonts/Supplemental/Verdana Bold Italic.ttf",
            },
            "trebuchet ms": {
                (False, False): "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf",
                (False, True): "/System/Library/Fonts/Supplemental/Trebuchet MS Italic.ttf",
            },
            "impact": {
                (False, False): "/System/Library/Fonts/Supplemental/Impact.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Impact.ttf",
            },
            "times new roman": {
                (False, False): "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
                (False, True): "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
            },
            "menlo": {
                (False, False): "/System/Library/Fonts/Menlo.ttc",
            },
            "comic sans ms": {
                (False, False): "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf",
            },
            "helvetica": {
                (False, False): "/System/Library/Fonts/Helvetica.ttc",
            }
        }
        key = (bool(bold), bool(italic))
        fam_key = str(family or "helvetica").strip().lower()
        variants = f_map.get(fam_key, f_map["helvetica"])
        font_path = variants.get(key) or variants.get((bold, False)) or variants.get((False, False)) or "/System/Library/Fonts/Helvetica.ttc"
        if not os.path.exists(font_path):
            font_path = "/System/Library/Fonts/Helvetica.ttc"
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            return ImageFont.load_default()

    def render_key_image(self, key_data: Dict[str, Any], is_pressed: bool = False) -> Image.Image:
        """Gera a imagem de uma tecla LCD com tipografia rica e micro-animação de pressão tátil."""
        bg = key_data.get("bg") or key_data.get("bg_color") or key_data.get("bgColor") or "#18181b"
        text_color = key_data.get("textColor", "#ffffff")
        accent = key_data.get("accent", None)
        title = key_data.get("title", "")
        subtitle = key_data.get("subtitle", "")
        font_size = int(key_data.get("fontSize", 14))
        font_family = key_data.get("fontFamily", "Helvetica")
        bold = bool(key_data.get("bold", False))
        italic = bool(key_data.get("italic", False))
        underline = bool(key_data.get("underline", False))
        show_title = bool(key_data.get("showTitle", True))
        title_align = str(key_data.get("titleAlignment", "middle")).lower()
        border_color = key_data.get("borderColor")
        border_width = int(key_data.get("borderWidth", 0))
        image_fit = str(key_data.get("imageFit", "cover")).lower()
        custom_image = key_data.get("imagePath", None)

        if custom_image:
            cand_path = custom_image
            if not os.path.isabs(cand_path):
                studio_cand = os.path.join(os.path.dirname(__file__), "studio", cand_path)
                if os.path.exists(studio_cand):
                    cand_path = studio_cand
            if os.path.exists(cand_path):
                try:
                    raw_img = Image.open(cand_path)
                    has_alpha = raw_img.mode in ("RGBA", "LA") or (raw_img.mode == "P" and "transparency" in raw_img.info)
                    if has_alpha or image_fit == "contain":
                        img = Image.new("RGBA", self.KEY_SIZE, color=bg)
                        raw_rgba = raw_img.convert("RGBA")
                        target_w, target_h = (int(self.KEY_SIZE[0] * 0.7), int(self.KEY_SIZE[1] * 0.7)) if has_alpha and show_title else self.KEY_SIZE
                        ratio = min(target_w / raw_rgba.width, target_h / raw_rgba.height)
                        nw, nh = max(1, int(raw_rgba.width * ratio)), max(1, int(raw_rgba.height * ratio))
                        resized_icon = raw_rgba.resize((nw, nh), Image.Resampling.LANCZOS)
                        offset_y = -10 if show_title and (title or subtitle) else 0
                        paste_x = (self.KEY_SIZE[0] - nw) // 2
                        paste_y = max(2, (self.KEY_SIZE[1] - nh) // 2 + offset_y)
                        img.paste(resized_icon, (paste_x, paste_y), mask=resized_icon)
                        img = img.convert("RGB")
                    else:
                        img = raw_img.convert("RGB").resize(self.KEY_SIZE, Image.Resampling.LANCZOS)
                except Exception:
                    img = Image.new("RGB", self.KEY_SIZE, color=bg)
            else:
                img = Image.new("RGB", self.KEY_SIZE, color=bg)
        else:
            img = Image.new("RGB", self.KEY_SIZE, color=bg)

        draw = ImageDraw.Draw(img)

        # Borda personalizada se configurada
        if border_width > 0 and border_color:
            try:
                draw.rounded_rectangle([(0, 0), (self.KEY_SIZE[0] - 1, self.KEY_SIZE[1] - 1)], radius=4, outline=border_color, width=border_width)
            except Exception:
                pass

        cx, cy = self.KEY_SIZE[0] // 2, self.KEY_SIZE[1] // 2
        act = key_data.get("action", {})
        act_type = str(act.get("type") or act.get("uuid") or "").lower()
        icon = str(key_data.get("icon") or "").lower()

        # Desenho de glifos vetorizados se não houver imagem customizada
        if not custom_image:
            # Se o título estiver oculto, desenha o ícone em modo ampliado/grande
            glyph_offset_y = 0 if not show_title else -16
            glyph_size_mult = 1.4 if not show_title else 1.0

            if icon == "arrow-left" or "backtoparent" in act_type:
                f_color = accent or "#007aff"
                draw.polygon([(cx - int(14 * glyph_size_mult), cy + glyph_offset_y),
                               (cx - int(4 * glyph_size_mult), cy + glyph_offset_y - int(8 * glyph_size_mult)),
                               (cx - int(4 * glyph_size_mult), cy + glyph_offset_y + int(8 * glyph_size_mult))], fill=f_color)
                draw.line([(cx - int(8 * glyph_size_mult), cy + glyph_offset_y),
                           (cx + int(12 * glyph_size_mult), cy + glyph_offset_y)], fill=f_color, width=3)
                draw.line([(cx + int(12 * glyph_size_mult), cy + glyph_offset_y),
                           (cx + int(12 * glyph_size_mult), cy + glyph_offset_y + int(6 * glyph_size_mult))], fill=f_color, width=3)
            elif icon == "folder" or "openchild" in act_type or act_type == "folder":
                f_color = accent or "#f59e0b"
                draw.rectangle([(cx - int(16 * glyph_size_mult), cy + glyph_offset_y - int(8 * glyph_size_mult)),
                                (cx - int(6 * glyph_size_mult), cy + glyph_offset_y - int(4 * glyph_size_mult))], fill=f_color)
                draw.rounded_rectangle([(cx - int(16 * glyph_size_mult), cy + glyph_offset_y - int(4 * glyph_size_mult)),
                                         (cx + int(16 * glyph_size_mult), cy + glyph_offset_y + int(10 * glyph_size_mult))], radius=2, fill=f_color)
            elif any(k in act_type for k in ("multiaction", "routine", "macro")) or icon in ("multiaction", "routine"):
                f_color = accent or "#a855f7"
                draw.line([(cx - 10, cy + glyph_offset_y - 6), (cx - 3, cy + glyph_offset_y)], fill=f_color, width=3)
                draw.line([(cx - 3, cy + glyph_offset_y), (cx - 10, cy + glyph_offset_y + 6)], fill=f_color, width=3)
                draw.line([(cx + 2, cy + glyph_offset_y - 6), (cx + 9, cy + glyph_offset_y)], fill=f_color, width=3)
                draw.line([(cx + 9, cy + glyph_offset_y), (cx + 2, cy + glyph_offset_y + 6)], fill=f_color, width=3)

        # Se o usuário optou por ocultar o título (DoNotShowTitle), encerra aqui
        if not show_title:
            return img

        # Resolução de Tipografia com fontes reais do macOS
        font_title = self._resolve_font(font_family, font_size, bold=bold, italic=italic)
        font_sub = self._resolve_font(font_family, max(9, font_size - 4), bold=False, italic=italic)

        # Alinhamento vertical
        if title_align == "top":
            y_base = cy - 20
        elif title_align == "bottom":
            y_base = cy + 20
        else:  # middle / center
            y_base = cy + (6 if not custom_image and icon in ("arrow-left", "folder", "multiaction", "routine") else 0)

        if title and subtitle:
            # Sombra de 1px para contraste
            draw.text((cx + 1, y_base - 7), title, fill="#000000", font=font_title, anchor="mm")
            draw.text((cx, y_base - 8), title, fill=text_color, font=font_title, anchor="mm")
            draw.text((cx + 1, y_base + 15), subtitle, fill="#000000", font=font_sub, anchor="mm")
            draw.text((cx, y_base + 14), subtitle, fill="#a1a1aa", font=font_sub, anchor="mm")

            if underline:
                bbox = draw.textbbox((cx, y_base - 8), title, font=font_title, anchor="mm")
                draw.line([(bbox[0], bbox[3] + 1), (bbox[2], bbox[3] + 1)], fill=text_color, width=1)
        elif title:
            lines = [l.strip() for l in title.split("\n") if l.strip()]
            if len(lines) == 1 and (" " in lines[0] or "-" in lines[0]):
                # Se for uma linha só mas tiver espaços e exceder o espaço da tecla, divide em 2 linhas
                words = lines[0].split()
                if len(words) >= 2:
                    mid = len(words) // 2
                    lines = [" ".join(words[:mid]), " ".join(words[mid:])]

            if len(lines) >= 2:
                draw.text((cx + 1, y_base - 9), lines[0], fill="#000000", font=font_title, anchor="mm")
                draw.text((cx, y_base - 10), lines[0], fill=text_color, font=font_title, anchor="mm")
                draw.text((cx + 1, y_base + 11), lines[1], fill="#000000", font=font_title, anchor="mm")
                draw.text((cx, y_base + 10), lines[1], fill=text_color, font=font_title, anchor="mm")
                if underline:
                    b1 = draw.textbbox((cx, y_base - 10), lines[0], font=font_title, anchor="mm")
                    b2 = draw.textbbox((cx, y_base + 10), lines[1], font=font_title, anchor="mm")
                    draw.line([(b1[0], b1[3] + 1), (b1[2], b1[3] + 1)], fill=text_color, width=1)
                    draw.line([(b2[0], b2[3] + 1), (b2[2], b2[3] + 1)], fill=text_color, width=1)
            else:
                draw.text((cx + 1, y_base + 1), title, fill="#000000", font=font_title, anchor="mm")
                draw.text((cx, y_base), title, fill=text_color, font=font_title, anchor="mm")
                if underline:
                    bbox = draw.textbbox((cx, y_base), title, font=font_title, anchor="mm")
                    draw.line([(bbox[0], bbox[3] + 1), (bbox[2], bbox[3] + 1)], fill=text_color, width=1)

        # Micro-animação tátil: compressão/afundamento da tecla com borda e escala reduzida
        if is_pressed:
            try:
                scale_factor = 0.85  # Redução de tamanho perceptível (15% menor) para sensação mecânica de clique
                target_w = max(10, int(self.KEY_SIZE[0] * scale_factor))
                target_h = max(10, int(self.KEY_SIZE[1] * scale_factor))
                scaled_img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                # Base preta profunda simulando a cavidade do switch mecânico
                pressed_canvas = Image.new("RGB", self.KEY_SIZE, color="#000000")
                px = (self.KEY_SIZE[0] - target_w) // 2
                py = (self.KEY_SIZE[1] - target_h) // 2

                # Máscara com cantos suavemente arredondados
                mask = Image.new("L", (target_w, target_h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([(0, 0), (target_w - 1, target_h - 1)], radius=6, fill=255)

                # Cola a tecla comprimida centralizada
                pressed_canvas.paste(scaled_img, (px, py), mask)

                # Desenha sutil borda de clique/contorno de luz mecânico
                p_draw = ImageDraw.Draw(pressed_canvas)
                highlight_color = accent if accent else "#3f3f46"
                p_draw.rounded_rectangle([(px, py), (px + target_w - 1, py + target_h - 1)], radius=6, outline=highlight_color, width=1)

                return pressed_canvas
            except Exception as e:
                print(f"[Engine] Erro ao renderizar estado pressionado da tecla: {e}")
                return img

        return img

    def apply_wallpaper_mural(self, image_path: str, page_id: Optional[str] = None) -> bool:
        """Divide uma imagem nos 15 slots da página (3x5) como um mural contínuo."""
        if not os.path.exists(image_path):
            return False
        if not page_id:
            page_id = self.config.get("active_page", "principal")
        if page_id not in self.config.get("pages", {}):
            return False

        try:
            wall = Image.open(image_path).convert("RGB")
            target_w, target_h = 5 * self.KEY_SIZE[0], 3 * self.KEY_SIZE[1]
            img_ratio = wall.width / wall.height
            target_ratio = target_w / target_h
            if img_ratio > target_ratio:
                new_h = target_h
                new_w = int(target_h * img_ratio)
            else:
                new_w = target_w
                new_h = int(target_w / img_ratio)
            resized = wall.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            cropped = resized.crop((left, top, left + target_w, top + target_h))

            out_dir = Path(__file__).resolve().parent / "studio" / "user_images"
            out_dir.mkdir(parents=True, exist_ok=True)

            page = self.config["pages"][page_id]
            if "keys" not in page:
                page["keys"] = {}

            ts = int(time.time())
            for row in range(3):
                for col in range(5):
                    slot = row * 5 + col + 1  # 1 a 15
                    box = (col * self.KEY_SIZE[0], row * self.KEY_SIZE[1], (col + 1) * self.KEY_SIZE[0], (row + 1) * self.KEY_SIZE[1])
                    tile = cropped.crop(box)
                    tile_filename = f"mural_{page_id}_{slot}_{ts}.jpg"
                    tile_path = out_dir / tile_filename
                    tile.save(tile_path, "JPEG", quality=92, progressive=False, optimize=False)

                    slot_str = str(slot)
                    if slot_str not in page["keys"]:
                        page["keys"][slot_str] = {}
                    page["keys"][slot_str]["imagePath"] = str(tile_path)
                    page["keys"][slot_str]["showTitle"] = False  # Mural de fundo sem texto poluindo

            self.save_config()
            if self.config.get("active_page") == page_id:
                self.sync_all_keys(force=True)
            return True
        except Exception as e:
            print(f"[Engine] Erro ao aplicar mural de wallpaper: {e}")
            return False

    def get_hw_key_for_slot(self, slot: int) -> int:
        """
        Converte o slot visual 5x3 (1 a 15) para o ID de hardware físico do Fifine AmpliGame D6:
        Fileira 1 (Topo):   Slot 1 -> 11 | Slot 2 -> 12 | Slot 3 -> 13 | Slot 4 -> 14 | Slot 5 -> 15
        Fileira 2 (Meio):   Slot 6 -> 6  | Slot 7 -> 7  | Slot 8 -> 8  | Slot 9 -> 9  | Slot 10 -> 10
        Fileira 3 (Base):   Slot 11 -> 1 | Slot 12 -> 2 | Slot 13 -> 3 | Slot 14 -> 4 | Slot 15 -> 5
        """
        fifine_official_map = {
            1: 11, 2: 12, 3: 13, 4: 14, 5: 15,
            6: 6,  7: 7,  8: 8,  9: 9,  10: 10,
            11: 1, 12: 2, 13: 3, 14: 4, 15: 5
        }
        return fifine_official_map.get(slot, slot)

    def get_slot_for_hw_key(self, hw_key: int) -> int:
        """Converte o clique físico recebido do hardware de volta para o slot visual 1 a 15."""
        fifine_official_rev = {
            11: 1, 12: 2, 13: 3, 14: 4, 15: 5,
            6: 6,  7: 7,  8: 8,  9: 9,  10: 10,
            1: 11, 2: 12, 3: 13, 4: 14, 5: 15
        }
        return fifine_official_rev.get(hw_key, hw_key)

    def sync_key(self, key_num: int, force: bool = False, is_pressed: bool = False, page_id: Optional[str] = None):
        """Envia a tecla atualizada diretamente para a tela LCD física com Dirty Checking ultra-rápido."""
        if not self.device or not (1 <= key_num <= 18):
            return

        if not page_id:
            page_id = self.config.get("active_page", "principal")
        page = self.config.get("pages", {}).get(page_id, {})
        key_data = page.get("keys", {}).get(str(key_num))

        hw_key = self.get_hw_key_for_slot(key_num)
        temp_path = f"/tmp/d6_key_{key_num}_{'p' if is_pressed else 'n'}.jpg"
        try:
            if key_data:
                img = self.render_key_image(key_data, is_pressed=is_pressed)
            else:
                img = self.render_empty_key_image()

            # Rotação base física do hardware Fifine D6 (180° com transposição exata de matriz, sem artefatos)
            rot = int(self.config.get("rotation", 0))
            total_rot = (180 + rot) % 360
            if total_rot == 180:
                img = img.transpose(Image.ROTATE_180)
            elif total_rot == 90:
                img = img.transpose(Image.ROTATE_90)
            elif total_rot == 270:
                img = img.transpose(Image.ROTATE_270)
            elif total_rot != 0:
                img = img.rotate(total_rot)

            # Salva JPEG baseline YUV 4:2:0 nativo com preenchimento 100% até o último pixel (sem mancha verde)
            img.save(temp_path, "JPEG", quality=95, progressive=False, optimize=False)

            # Dirty Checking com Hash MD5: se a imagem for idêntica ao que já está no LCD, pula transmissão USB
            import hashlib
            with open(temp_path, "rb") as f:
                img_hash = hashlib.md5(f.read()).hexdigest()

            if not force and self._displayed_key_hashes.get(hw_key) == img_hash:
                return  # Já está exibida no hardware! 0ms de latência!

            with self.lock:
                if hasattr(self.device, "transport"):
                    res = self.device.transport.setKeyImg(bytes(temp_path, "utf-8"), hw_key)
                elif hasattr(self.device, "set_key_image"):
                    res = self.device.set_key_image(key_num, temp_path)
                else:
                    res = -1

                if hasattr(self.device, "refresh"):
                    self.device.refresh()
            
            self._displayed_key_hashes[hw_key] = img_hash
        except Exception as e:
            print(f"[Engine] Erro ao sincronizar tecla {key_num}: {e}")

    def animate_key_press(self, slot_num: int, duration: float = 0.18):
        """Micro-animação tátil de compressão (scale-down 85%) na tela LCD física."""
        if not self.device or not (1 <= slot_num <= 15):
            return

        def _press_thread():
            try:
                # 1. Envia frame de botão pressionado (tamanho reduzido para 82x82 com borda de toque)
                self.sync_key(slot_num, force=True, is_pressed=True)
                time.sleep(duration)
                # 2. Retorna ao tamanho original normal
                self.sync_key(slot_num, force=True, is_pressed=False)
            except Exception as e:
                print(f"[Engine] Erro na micro-animação da tecla {slot_num}: {e}")

        threading.Thread(target=_press_thread, daemon=True).start()

    def sync_all_keys(self, force: bool = True):
        """Atualiza todas as 15 telas do deck físico com retransmissão completa e segura."""
        if not self.device:
            return

        active_page = self.config.get("active_page", "principal")
        for k in range(1, 16):
            self.sync_key(k, force=force, page_id=active_page)
            # Intervalo mínimo seguro (8ms) para o microcontrolador do 293S
            time.sleep(0.008)

        # Atualiza o display no hardware se suportado
        if hasattr(self.device, "refresh"):
            with self.lock:
                self.device.refresh()

    def change_page(self, page_id: str, is_auto: bool = False):
        if page_id in self.config.get("pages", {}):
            if not is_auto:
                self._last_manual_page = page_id
                self._auto_switched = False
            self.config["active_page"] = page_id
            self.save_config()
            # Limpa hashes em memória para forçar a reescrita de todas as 15 telas no LCD físico
            self._displayed_key_hashes.clear()
            self.sync_all_keys(force=True)
            print(f"[Engine] Mudou para página: {page_id} (auto={is_auto})")

    def get_frontmost_app(self) -> Optional[Dict[str, str]]:
        """Detecta o aplicativo ativo em primeiro plano no macOS via lsappinfo nativo (< 15ms)."""
        try:
            res = subprocess.run(
                ["/bin/sh", "-c", "lsappinfo info -only name -only bundleid -only bundlepath $(lsappinfo front)"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if res.returncode == 0 and res.stdout:
                lines = res.stdout.strip().split("\n")
                name = ""
                bundle_id = ""
                bundle_path = ""
                first_line = lines[0].strip()
                if '"' in first_line:
                    parts = first_line.split('"')
                    if len(parts) >= 2:
                        name = parts[1]
                for line in lines[1:]:
                    line_s = line.strip()
                    if line_s.startswith('bundleID="'):
                        bundle_id = line_s[len('bundleID="'):-1]
                    elif line_s.startswith('bundle path="'):
                        bundle_path = line_s[len('bundle path="'):-1]
                return {"name": name, "bundle_id": bundle_id, "path": bundle_path}
        except Exception:
            pass
        return None

    def check_app_auto_switch(self):
        """Verifica o aplicativo ativo no macOS e troca de perfil automaticamente se vinculado."""
        if not self.config.get("auto_switch_enabled", True):
            return

        app_info = self.get_frontmost_app()
        if not app_info or not app_info.get("name"):
            return

        app_name = app_info["name"]
        app_name_lower = app_name.lower()
        bundle_id_lower = app_info.get("bundle_id", "").lower()
        path_lower = app_info.get("path", "").lower()

        # Procura se alguma página/perfil está vinculada a este aplicativo
        matched_page_id = None
        for pid, page in self.config.get("pages", {}).items():
            if page.get("is_folder"):
                continue
            linked = str(page.get("linked_app") or "").strip().lower()
            if not linked:
                continue

            # Casamento por nome, bundle ID, nome do executável ou caminho
            if (linked == app_name_lower or 
                linked == bundle_id_lower or 
                linked in path_lower or 
                linked == os.path.basename(path_lower).replace(".app", "").lower()):
                matched_page_id = pid
                break

        current_page = self.config.get("active_page", "principal")

        # Se o estado do teclado já reflete exatamente este app em foco, retorna
        if app_name == self._last_frontmost_app_name:
            if matched_page_id and current_page == matched_page_id:
                return
            if not matched_page_id and not self._auto_switched:
                return

        self._last_frontmost_app_name = app_name

        if matched_page_id:
            if current_page != matched_page_id:
                print(f"[Auto-Switch] App '{app_name}' em foco -> Trocando para cena '{matched_page_id}'")
                self.change_page(matched_page_id, is_auto=True)
                self._auto_switched = True
        else:
            # O aplicativo ativo não tem cena vinculada
            if self._auto_switched:
                fallback = self._last_manual_page
                if fallback not in self.config.get("pages", {}):
                    fallback = "principal"
                if current_page != fallback:
                    print(f"[Auto-Switch] App '{app_name}' sem vínculo -> Retornando para '{fallback}'")
                    self.change_page(fallback, is_auto=True)
                self._auto_switched = False

    def _send_hotkey(self, hotkey_str: str):
        """Envia combinações de atalho com modificadores (Cmd, Ctrl, Alt, Shift) via osascript."""
        if not hotkey_str:
            return
        raw_str = str(hotkey_str).replace(" - ", "+").replace("-", "+")
        parts = [p.strip() for p in raw_str.split("+") if p.strip()]
        modifiers = []
        main_key = ""
        for p in parts:
            p_up = p.upper()
            if p_up in ("CMD", "COMMAND"):
                modifiers.append("command down")
            elif p_up in ("CTRL", "CONTROL"):
                modifiers.append("control down")
            elif p_up in ("ALT", "OPTION"):
                modifiers.append("option down")
            elif p_up in ("SHIFT",):
                modifiers.append("shift down")
            else:
                main_key = p

        using_str = f" using {{{', '.join(modifiers)}}}" if modifiers else ""

        key_code_map = {
            "RETURN": 36, "ENTER": 36, "TAB": 48, "SPACE": 49, "BACKSPACE": 51, "DELETE": 117,
            "ESCAPE": 53, "ESC": 53, "UP": 126, "DOWN": 125, "LEFT": 123, "RIGHT": 124,
            "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97,
            "F7": 98, "F8": 100, "F9": 101, "F10": 109, "F11": 103, "F12": 111
        }

        if main_key.upper() in key_code_map:
            code = key_code_map[main_key.upper()]
            cmd = f'tell application "System Events" to key code {code}{using_str}'
        else:
            k_char = main_key.lower() if len(main_key) == 1 else main_key
            cmd = f'tell application "System Events" to keystroke "{k_char}"{using_str}'

        try:
            subprocess.run(["osascript", "-e", cmd], timeout=2)
        except Exception as e:
            print(f"[Engine] Erro ao enviar hotkey '{hotkey_str}': {e}")

    @staticmethod
    def open_target_on_mac(target: str) -> bool:
        """Abre qualquer aplicativo, arquivo, pasta ou comando no macOS com resolução inteligente."""
        target = str(target or "").strip()
        if not target:
            return False

        # 1. Caminho existente diretamente (com expanduser para suportar ~)
        expanded = os.path.expanduser(target)
        if os.path.exists(expanded):
            print(f"[Engine Open] Abrindo caminho existente no macOS: '{expanded}'")
            subprocess.Popen(["open", expanded])
            return True

        # 2. Extrai nome base do app (eliminando diretórios inexistentes e extensões .zip/.app)
        raw_name = os.path.basename(target)
        clean_name = raw_name[:-4] if raw_name.lower().endswith(".zip") else raw_name
        clean_name = clean_name[:-4] if clean_name.lower().endswith(".app") else clean_name

        # 3. Busca nas pastas padrão do macOS pelo nome limpo
        app_dirs = [
            "/Applications",
            "/System/Applications",
            "/System/Applications/Utilities",
            os.path.expanduser("~/Applications"),
            os.path.expanduser("~/Downloads"),
            "/Applications/Utilities"
        ]
        for app_dir in app_dirs:
            if not os.path.exists(app_dir):
                continue
            cand = os.path.join(app_dir, f"{clean_name}.app")
            if os.path.exists(cand):
                print(f"[Engine Open] Encontrado aplicativo em '{cand}' -> Abrindo")
                subprocess.Popen(["open", cand])
                return True

        # 4. Tenta 'open -a' pelo nome limpo do app (ex: 'open -a ResetCamera', 'open -a Safari')
        if clean_name:
            print(f"[Engine Open] Tentando 'open -a \"{clean_name}\"'...")
            r = subprocess.run(["open", "-a", clean_name], capture_output=True, text=True)
            if r.returncode == 0:
                print(f"[Engine Open] Sucesso ao abrir '{clean_name}' via 'open -a'")
                return True

        # 5. Tenta 'open -a' com o target original
        r = subprocess.run(["open", "-a", target], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[Engine Open] Sucesso ao abrir '{target}' via 'open -a'")
            return True

        # 6. Fallback final genérico 'open' (para URLs, arquivos com app padrão, etc.)
        print(f"[Engine Open] Fallback genérico 'open \"{target}\"'...")
        subprocess.Popen(["open", target])
        return True

    def execute_action(self, action: Dict[str, Any], slot: Optional[int] = None) -> bool:
        """Executa a ação correspondente via ActionRegistry (Command Pattern modular)."""
        if not action or not isinstance(action, dict):
            return False

        try:
            return ActionRegistry.dispatch(action, slot=slot, engine=self)
        except Exception as e:
            print(f"[Engine Action Error] {e}")
            return False

    def _update_mic_keys(self, mic_on: bool):
        page_id = self.config.get("active_page", "principal")
        page = self.config.get("pages", {}).get(page_id, {})
        for k_str, k_data in page.get("keys", {}).items():
            if k_data.get("action", {}).get("type") == "mic_toggle":
                k_data["title"] = "MIC ON" if mic_on else "MUTED"
                k_data["bg"] = "#14532d" if mic_on else "#7f1d1d"
                k_data["accent"] = "#22c55e" if mic_on else "#ef4444"
                self.sync_key(int(k_str))

    def _on_hardware_key(self, *args, **kwargs):
        """Callback unificado compatível com chamadas do SDK (device, event) ou (deck, key, state)."""
        key_val = None
        state = 0

        if len(args) >= 2:
            event = args[1]
            if hasattr(event, "event_type"):
                from StreamDock.InputTypes import EventType
                if event.event_type != EventType.BUTTON:
                    return
                key_val = event.key.value if hasattr(event.key, "value") else int(event.key)
                state = getattr(event, "state", 0)
            elif len(args) >= 3:
                key_val = event.value if hasattr(event, "value") else int(event)
                state = args[2]

        if state == 1 and key_val is not None:  # Key down
            # Qualquer interação física no hardware reseta a inatividade
            self.reset_inactivity()
            self._last_web_activity_time = time.time()

            # Se o hardware estiver em modo repouso (Sleep / Burn-in Protection), o toque apenas acorda o teclado
            if getattr(self, "is_asleep", False):
                print(f"[Engine] Tecla física {key_val} pressionada em Sleep -> Acordando Stream Deck (Wake up)")
                self.wake_device()
                return  # Consome o primeiro clique como despertar (1:1 com StreamDeck oficial)

            # Resolução resiliente de slot visual: prioriza o slot visual direto key_val
            mapped_slot = self.get_slot_for_hw_key(key_val)
            candidates = [key_val, mapped_slot]

            page_id = self.config.get("active_page", "principal")
            page = self.config.get("pages", {}).get(page_id, {})
            keys_dict = page.get("keys", {})

            def has_executable_action(k_dict):
                if not k_dict or not isinstance(k_dict, dict):
                    return False
                act = k_dict.get("action")
                if isinstance(act, dict):
                    t = str(act.get("type") or act.get("uuid") or "").lower()
                    if t and t not in ("none", "action"):
                        return True
                    if act.get("target") or act.get("path") or act.get("url") or act.get("keys") or act.get("text") or act.get("command"):
                        return True
                at = str(k_dict.get("actionType") or k_dict.get("type") or k_dict.get("uuid") or "").lower()
                if at and at not in ("none", "action"):
                    return True
                if k_dict.get("path") or k_dict.get("target") or k_dict.get("url") or k_dict.get("hotkey") or k_dict.get("textPayload"):
                    return True
                return False

            key_data = None
            target_slot = key_val
            for cand in candidates:
                cand_data = keys_dict.get(str(cand))
                if cand_data and has_executable_action(cand_data):
                    key_data = cand_data
                    target_slot = cand
                    break

            if key_data is None:
                key_data = keys_dict.get(str(key_val)) or keys_dict.get(str(mapped_slot))
                target_slot = key_val

            print(f"[Hardware Click] Tecla física {key_val} -> Slot visual resolvido {target_slot} na página '{page_id}'")

            # Registra timestamp e slot para sincronização em tempo real com a Web UI
            self._last_pressed_slot = target_slot
            self._last_pressed_ts = time.time()

            # Dispara micro-animação tátil de compressão (escala reduzida no LCD do hardware)
            self.animate_key_press(target_slot)

            action = None
            if key_data:
                if "action" in key_data and key_data["action"] and isinstance(key_data["action"], dict):
                    action = key_data["action"]
                else:
                    act_type = key_data.get("actionType") or key_data.get("type") or key_data.get("uuid")
                    if act_type and act_type != "none":
                        action = {
                            "type": act_type,
                            "target": key_data.get("target") or key_data.get("path") or key_data.get("url"),
                            "path": key_data.get("path"),
                            "text": key_data.get("textPayload") or key_data.get("text"),
                            "keys": key_data.get("hotkey") or key_data.get("keys"),
                            "command": key_data.get("command") or key_data.get("cmd"),
                            "uuid": key_data.get("uuid") or key_data.get("actionUuid")
                        }

            if action:
                print(f"[Hardware Action] Executando ação do slot {target_slot}: {action}")
                threading.Thread(target=self.execute_action, args=(action, target_slot), daemon=True).start()
            else:
                print(f"[Hardware Action] Nenhuma ação configurada no slot {target_slot}")

    def start_background_telemetry(self):
        """Loop de fundo para métricas dinâmicas (CPU, RAM), auto-troca de perfil e temporizador de inatividade."""
        self.running = True

        def loop():
            while self.running:
                try:
                    now = time.time()

                    # 0. LED Seguir Modo de Suspensão do macOS (DisconnectOnScreenOff / LED Sleep Follow)
                    follow_mac = self.config.get("led_sleep_follow", True)
                    if follow_mac:
                        mac_off = self.is_mac_screen_off_or_locked()
                        if mac_off:
                            if not self.is_asleep:
                                self._slept_by_mac_display = True
                                self.sleep_device(reason="macOS Tela Desligada / Bloqueada")
                            time.sleep(0.35)
                            continue
                        else:
                            if self.is_asleep and getattr(self, "_slept_by_mac_display", False):
                                self._slept_by_mac_display = False
                                self.wake_device(reason="macOS Tela Ligada / Desbloqueada")

                    # 1. Temporizador de Inatividade / Economia de Energia (Sleep & Burn-in Protection)
                    timeout = int(self.config.get("screen_off_seconds", 0))
                    if timeout > 0:
                        if not self.is_asleep and (now - self._last_activity_time >= timeout):
                            self.sleep_device(reason=f"Inatividade de {timeout}s")
                        elif self.is_asleep and not getattr(self, "_slept_by_mac_display", False):
                            # Se o usuário voltou a interagir ativamente com o Mac (mouse/teclado < 1.5s)
                            if self.get_mac_hid_idle_time() < 1.5:
                                print("[Engine] Atividade recente de mouse/teclado no macOS -> Acordando teclado")
                                self.wake_device(reason="Atividade no macOS")

                    # 2. Checagem de auto-troca de perfil pelo app ativo no macOS (a cada 0.7s)
                    if not self.is_asleep and (now - self._last_app_check_time >= 0.7):
                        self._last_app_check_time = now
                        self.check_app_auto_switch()

                    # 3. Métricas de CPU / RAM (a cada 3.0s, apenas se acordado)
                    if not self.is_asleep and (now - self._last_stats_update >= 3.0):
                        self._last_stats_update = now
                        page_id = self.config.get("active_page", "principal")
                        page = self.config.get("pages", {}).get(page_id, {})
                        
                        # Calcula carga aproximada
                        load = os.getloadavg()[0]
                        cpu_pct = min(100, int(load * 18))
                        
                        updated = False
                        for k_str, k_data in page.get("keys", {}).items():
                            act = k_data.get("action", {})
                            if act.get("type") == "system_stats":
                                tgt = act.get("target")
                                if tgt == "cpu":
                                    k_data["subtitle"] = f"{cpu_pct}%"
                                    self.sync_key(int(k_str))
                                    updated = True
                                elif tgt == "ram":
                                    k_data["subtitle"] = "OK"
                                    self.sync_key(int(k_str))
                                    updated = True
                except Exception as err:
                    pass
                time.sleep(0.35)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
