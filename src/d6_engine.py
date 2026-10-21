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
SDK_PATH = Path(__file__).resolve().parent.parent / "sdk"
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
    "startup_screen_mode": "black",
    "startup_screen_path": "",
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
    KEY_SIZE = (100, 100)  # Resolução perfeita validada fisicamente no hardware Fifine AmpliGame D6

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
                    key_id = "principal" if norm in ("cena_padrao", "padrao", "default") else norm

                # Se a página foi explicitamente excluída pelo usuário, não ressuscite
                deleted_pages = config.get("deleted_pages", [])
                if key_id in deleted_pages or p_dir.name in deleted_pages:
                    continue

                is_brand_new_page = key_id not in config["pages"]
                if is_brand_new_page:
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

                # Importa ações do manifest APENAS SE FOR UMA PÁGINA NOVA!
                # Se a página já existe no config, d6_profiles.json é a fonte soberana de verdade!
                if not is_brand_new_page:
                    continue

                # Importa ações contidas no manifest
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

    def delete_page(self, page_id: str) -> bool:
        """Exclui permanentemente uma página do sistema, removendo a pasta nativa e o backup no disco."""
        if not page_id or page_id == "principal" or page_id not in self.config.get("pages", {}):
            return False

        page_info = self.config["pages"].pop(page_id, {})
        native_folder = page_info.get("native_folder")

        # 1. Registra na lista de páginas excluídas para imunizar contra re-importações
        if "deleted_pages" not in self.config:
            self.config["deleted_pages"] = []
        if page_id not in self.config["deleted_pages"]:
            self.config["deleted_pages"].append(page_id)
        if native_folder and native_folder not in self.config["deleted_pages"]:
            self.config["deleted_pages"].append(native_folder)

        # 2. Exclusão física da pasta .sdProfile no disco oficial e backup
        if native_folder:
            import shutil
            streamdock_profiles = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles"
            p_dir = streamdock_profiles / native_folder
            if p_dir.exists():
                try:
                    shutil.rmtree(p_dir, ignore_errors=True)
                except Exception as e:
                    print(f"[Engine] Erro ao remover pasta de perfil {native_folder}: {e}")

            backup_dir = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles_golden_backup"
            b_dir = backup_dir / native_folder
            if b_dir.exists():
                try:
                    shutil.rmtree(b_dir, ignore_errors=True)
                except Exception as e:
                    print(f"[Engine] Erro ao remover backup do perfil {native_folder}: {e}")

        if self.config.get("active_page") == page_id:
            self.change_page("principal")

        self.save_config()
        return True

    def remove_key_from_native_manifest(self, page_id: str, slot_num: int):
        """Remove a ação correspondente do manifest.json nativo no disco para evitar ressurreição."""
        page_info = self.config.get("pages", {}).get(page_id, {})
        native_folder = page_info.get("native_folder")
        if not native_folder:
            return

        m_path = Path.home() / "Library" / "Application Support" / "HotSpot" / "StreamDock" / "profiles" / native_folder / "manifest.json"
        if not m_path.exists():
            return

        try:
            with open(m_path, "r", encoding="utf-8") as f:
                m_data = json.load(f)
            actions = m_data.get("Actions", {})

            # Calcula coordenadas (x, y) no grid 5x3 a partir de slot_num 1 a 15
            x = (slot_num - 1) % 5
            y = (slot_num - 1) // 5
            coord = f"{x},{y}"

            if coord in actions:
                del actions[coord]
                with open(m_path, "w", encoding="utf-8") as f:
                    json.dump(m_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Engine] Erro ao limpar tecla do manifest nativo: {e}")

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

            # Clear any stale icons from previous sessions/apps
            try:
                self.device.clearAllIcon()
            except Exception as clear_err:
                print(f"[Engine] Note: clearAllIcon during connect: {clear_err}")

            # Apply startup background screen to override old vendor flash image
            startup_mode = self.config.get("startup_screen_mode", "black")
            startup_path = self.config.get("startup_screen_path")
            try:
                if startup_mode == "custom" and startup_path and os.path.exists(startup_path):
                    self.set_startup_screen(startup_path, persist=False)
                else:
                    self.reset_startup_screen(persist=False)
            except Exception as bg_err:
                print(f"[Engine] Note: Error updating hardware background screen: {bg_err}")

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
        img = Image.new("RGB", self.KEY_SIZE, color="#000000")
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (self.KEY_SIZE[0] - 1, self.KEY_SIZE[1] - 1)], outline="#000000", width=1)
        return img

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
                (False, False): ("/System/Library/Fonts/Menlo.ttc", 0),
                (True, False): ("/System/Library/Fonts/Menlo.ttc", 1),
                (False, True): ("/System/Library/Fonts/Menlo.ttc", 2),
                (True, True): ("/System/Library/Fonts/Menlo.ttc", 3),
            },
            "comic sans ms": {
                (False, False): "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
                (True, False): "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf",
            },
            "helvetica": {
                (False, False): ("/System/Library/Fonts/Helvetica.ttc", 0),
                (True, False): ("/System/Library/Fonts/Helvetica.ttc", 1),
                (False, True): ("/System/Library/Fonts/Helvetica.ttc", 2),
                (True, True): ("/System/Library/Fonts/Helvetica.ttc", 3),
            },
            "helvetica neue": {
                (False, False): ("/System/Library/Fonts/HelveticaNeue.ttc", 0),
                (True, False): ("/System/Library/Fonts/HelveticaNeue.ttc", 1),
                (False, True): ("/System/Library/Fonts/HelveticaNeue.ttc", 2),
                (True, True): ("/System/Library/Fonts/HelveticaNeue.ttc", 3),
            }
        }
        key = (bool(bold), bool(italic))
        fam_key = str(family or "helvetica").strip().lower()
        variants = f_map.get(fam_key, f_map["helvetica"])
        font_val = variants.get(key) or variants.get((bold, False)) or variants.get((False, False)) or ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0)
        
        if isinstance(font_val, tuple):
            font_path, font_index = font_val
        else:
            font_path, font_index = str(font_val), (1 if bold else 0) if str(font_val).endswith(".ttc") else 0

        if not os.path.exists(font_path):
            font_path = "/System/Library/Fonts/Helvetica.ttc"
            font_index = 1 if bold else 0
        try:
            if font_path.endswith(".ttc"):
                return ImageFont.truetype(font_path, size, index=font_index)
            return ImageFont.truetype(font_path, size)
        except Exception:
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

        act = key_data.get("action", {})
        act_type = str(act.get("type") or act.get("uuid") or "").lower()
        icon = str(key_data.get("icon") or "").lower()
        is_app_launcher = act_type == "open_app" or (act_type in ("website", "open_url") and not show_title)

        custom_image = key_data.get("imagePath", None)
        if not custom_image:
            act_uuid = str(act.get("uuid") or key_data.get("uuid") or act.get("type") or "").strip()
            if act_uuid:
                for cand in (
                    f"assets/native_icons/{act_uuid}_btn.jpg",
                    f"assets/native_icons/{act_uuid}_btn.png",
                    f"assets/native_icons/{act_uuid}_icon.png",
                    f"assets/native_icons/{act_uuid}_icon.jpg",
                ):
                    studio_cand = os.path.join(os.path.dirname(__file__), "studio", cand)
                    if os.path.exists(studio_cand):
                        custom_image = studio_cand
                        break

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
                    if has_alpha or image_fit == "contain" or is_app_launcher:
                        img = Image.new("RGBA", self.KEY_SIZE, color=bg)
                        raw_rgba = raw_img.convert("RGBA")
                        # Para launcher de apps, ícone grande (76x76) ocupando o centro da tecla com margem elegante
                        target_w, target_h = (76, 76) if is_app_launcher else ((int(self.KEY_SIZE[0] * 0.7), int(self.KEY_SIZE[1] * 0.7)) if has_alpha and show_title else self.KEY_SIZE)
                        ratio = min(target_w / raw_rgba.width, target_h / raw_rgba.height)
                        nw, nh = max(1, int(raw_rgba.width * ratio)), max(1, int(raw_rgba.height * ratio))
                        resized_icon = raw_rgba.resize((nw, nh), Image.Resampling.LANCZOS)
                        offset_y = 0 if is_app_launcher else (-10 if show_title and (title or subtitle) else 0)
                        paste_x = (self.KEY_SIZE[0] - nw) // 2
                        paste_y = max(2, (self.KEY_SIZE[1] - nh) // 2 + offset_y)
                        img.paste(resized_icon, (paste_x, paste_y), mask=resized_icon)
                        img = img.convert("RGB")
                        if is_app_launcher:
                            return img  # Retorna o ícone do app em alta resolução sem texto atrapalhando!
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

        # Layout Especial para Métricas / HUD (Números Gigantes de altíssima legibilidade + Barra Visual Dinâmica)
        if act_type in ("system_stats", "systemstats"):
            f_header = self._resolve_font(font_family, 11, bold=True)
            f_huge = self._resolve_font(font_family, 24, bold=True)

            val_text = subtitle or "--"
            sub_unit = ""
            if "livre" in val_text.lower():
                parts = val_text.split()
                val_text = parts[0]
                sub_unit = " ".join(parts[1:])

            accent_col = accent or "#38bdf8"
            txt_col = text_color or "#ffffff"

            pct = 0
            try:
                import re
                m_pct = re.search(r"(\d+)", val_text)
                if m_pct:
                    val_int = int(m_pct.group(1))
                    tgt_l = str(act.get("target", "")).lower()
                    if tgt_l == "disk" or "ssd" in tgt_l:
                        import shutil
                        tot, used, _ = shutil.disk_usage("/")
                        pct = min(100, max(0, int((used / tot) * 100)))
                    elif tgt_l in ("ping", "rede", "net"):
                        pct = min(100, max(5, int((val_int / 80.0) * 100)))
                    else:
                        pct = min(100, max(0, val_int))
            except Exception:
                pct = 50

            gauge_style = str(act.get("style") or key_data.get("gaugeStyle") or "").lower()
            if not gauge_style:
                tgt_l = str(act.get("target", "")).lower()
                gauge_style = "arc" if tgt_l in ("cpu", "ram") else "bar"

            if gauge_style == "arc":
                # Mostrador Radial Circular de Alta Resolução
                arc_bbox = [(14, 12), (86, 84)]
                # Fundo do arco (270 graus: 135 a 405)
                draw.arc(arc_bbox, start=135, end=405, fill="#27272a", width=6)
                # Arco preenchido proporcional
                arc_end = 135 + int(270 * (pct / 100.0))
                if pct > 0:
                    draw.arc(arc_bbox, start=135, end=arc_end, fill=accent_col, width=6)
                # Título compacto no topo
                f_arc_title = self._resolve_font(font_family, 10, bold=True)
                draw.text((cx, 32), (title or "STAT").upper(), fill="#94a3b8", font=f_arc_title, anchor="mm")
                # Valor central
                f_arc_val = self._resolve_font(font_family, 18, bold=True)
                draw.text((cx, 54), val_text, fill=txt_col, font=f_arc_val, anchor="mm")
                return img

            # Estilo Barra Horizontal (com marcadores e visual de alta fidelidade)
            draw.text((cx, 16), (title or "STAT").upper(), fill="#94a3b8", font=f_header, anchor="mm")
            draw.text((cx, 44), val_text, fill=accent_col, font=f_huge, anchor="mm")

            track_w = 74
            x1, x2 = cx - track_w // 2, cx + track_w // 2
            y1, y2 = 70, 80

            fill_w = int(track_w * (pct / 100.0))
            # Track com contorno visível definindo a capacidade total (100%)
            draw.rounded_rectangle([(x1, y1), (x2, y2)], radius=4, fill="#27272a", outline="#52525b", width=1)
            # Preenchimento dinâmico do percentual utilizado
            if fill_w > 0:
                draw.rounded_rectangle([(x1, y1), (x1 + max(6, fill_w), y2)], radius=4, fill=accent_col)
            # Marcadores de referência discretos a 25%, 50% e 75%
            for mark in (0.25, 0.50, 0.75):
                mx = x1 + int(track_w * mark)
                if mx > x1 + fill_w + 3 and mx < x2 - 2:
                    draw.line([(mx, y1 + 2), (mx, y2 - 2)], fill="#52525b", width=1)

            return img

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
            elif icon == "cpu":
                f_color = accent or "#38bdf8"
                draw.rectangle([(cx - 9, cy + glyph_offset_y - 9), (cx + 9, cy + glyph_offset_y + 9)], outline=f_color, width=2)
                draw.rectangle([(cx - 4, cy + glyph_offset_y - 4), (cx + 4, cy + glyph_offset_y + 4)], fill=f_color)
                for p in (-5, 0, 5):
                    draw.line([(cx + p, cy + glyph_offset_y - 12), (cx + p, cy + glyph_offset_y - 9)], fill=f_color, width=1)
                    draw.line([(cx + p, cy + glyph_offset_y + 9), (cx + p, cy + glyph_offset_y + 12)], fill=f_color, width=1)
                    draw.line([(cx - 12, cy + glyph_offset_y + p), (cx - 9, cy + glyph_offset_y + p)], fill=f_color, width=1)
                    draw.line([(cx + 9, cy + glyph_offset_y + p), (cx + 12, cy + glyph_offset_y + p)], fill=f_color, width=1)
            elif icon in ("ram", "memory"):
                f_color = accent or "#a855f7"
                draw.rectangle([(cx - 11, cy + glyph_offset_y - 6), (cx + 11, cy + glyph_offset_y + 6)], outline=f_color, width=2)
                for p in (-7, -3, 1, 5):
                    draw.rectangle([(cx + p, cy + glyph_offset_y - 3), (cx + p + 2, cy + glyph_offset_y + 3)], fill=f_color)
            elif icon in ("hard-drive", "disk"):
                f_color = accent or "#34d399"
                draw.rounded_rectangle([(cx - 12, cy + glyph_offset_y - 6), (cx + 12, cy + glyph_offset_y + 6)], radius=2, outline=f_color, width=2)
                draw.ellipse([(cx + 6, cy + glyph_offset_y - 2), (cx + 9, cy + glyph_offset_y + 1)], fill=f_color)
                draw.line([(cx - 8, cy + glyph_offset_y), (cx + 2, cy + glyph_offset_y)], fill=f_color, width=1)
            elif icon == "terminal":
                f_color = accent or "#e4e4e7"
                draw.line([(cx - 10, cy + glyph_offset_y - 6), (cx - 4, cy + glyph_offset_y)], fill=f_color, width=2)
                draw.line([(cx - 4, cy + glyph_offset_y), (cx - 10, cy + glyph_offset_y + 6)], fill=f_color, width=2)
                draw.line([(cx - 1, cy + glyph_offset_y + 6), (cx + 8, cy + glyph_offset_y + 6)], fill=f_color, width=2)
            elif icon == "activity":
                f_color = accent or "#38bdf8"
                draw.line([(cx - 12, cy + glyph_offset_y), (cx - 6, cy + glyph_offset_y)], fill=f_color, width=2)
                draw.line([(cx - 6, cy + glyph_offset_y), (cx - 2, cy + glyph_offset_y - 8)], fill=f_color, width=2)
                draw.line([(cx - 2, cy + glyph_offset_y - 8), (cx + 2, cy + glyph_offset_y + 8)], fill=f_color, width=2)
                draw.line([(cx + 2, cy + glyph_offset_y + 8), (cx + 6, cy + glyph_offset_y)], fill=f_color, width=2)
                draw.line([(cx + 6, cy + glyph_offset_y), (cx + 12, cy + glyph_offset_y)], fill=f_color, width=2)
            elif icon == "lock":
                f_color = accent or "#eab308"
                draw.rounded_rectangle([(cx - 9, cy + glyph_offset_y - 2), (cx + 9, cy + glyph_offset_y + 9)], radius=2, fill=f_color)
                draw.arc([(cx - 6, cy + glyph_offset_y - 12), (cx + 6, cy + glyph_offset_y)], start=180, end=0, fill=f_color, width=2)
            elif icon == "moon":
                f_color = accent or "#6366f1"
                draw.arc([(cx - 8, cy + glyph_offset_y - 8), (cx + 8, cy + glyph_offset_y + 8)], start=60, end=300, fill=f_color, width=2)
                draw.arc([(cx - 13, cy + glyph_offset_y - 8), (cx + 3, cy + glyph_offset_y + 8)], start=60, end=300, fill=f_color, width=2)
            elif icon == "camera":
                f_color = accent or "#06b6d4"
                draw.rounded_rectangle([(cx - 11, cy + glyph_offset_y - 4), (cx + 11, cy + glyph_offset_y + 9)], radius=2, outline=f_color, width=2)
                draw.rectangle([(cx - 5, cy + glyph_offset_y - 8), (cx + 2, cy + glyph_offset_y - 4)], fill=f_color)
                draw.ellipse([(cx - 4, cy + glyph_offset_y - 1), (cx + 4, cy + glyph_offset_y + 7)], outline=f_color, width=2)
            elif icon in ("volume-x", "mute"):
                f_color = accent or "#ec4899"
                draw.polygon([(cx - 10, cy + glyph_offset_y - 4), (cx - 5, cy + glyph_offset_y - 4), (cx - 1, cy + glyph_offset_y - 8), (cx - 1, cy + glyph_offset_y + 8), (cx - 5, cy + glyph_offset_y + 4), (cx - 10, cy + glyph_offset_y + 4)], fill=f_color)
                draw.line([(cx + 4, cy + glyph_offset_y - 4), (cx + 10, cy + glyph_offset_y + 4)], fill=f_color, width=2)
                draw.line([(cx + 10, cy + glyph_offset_y - 4), (cx + 4, cy + glyph_offset_y + 4)], fill=f_color, width=2)
            elif icon in ("trash-2", "trash"):
                f_color = accent or "#f59e0b"
                draw.line([(cx - 10, cy + glyph_offset_y - 6), (cx + 10, cy + glyph_offset_y - 6)], fill=f_color, width=2)
                draw.rounded_rectangle([(cx - 7, cy + glyph_offset_y - 4), (cx + 7, cy + glyph_offset_y + 9)], radius=2, outline=f_color, width=2)
                draw.line([(cx - 2, cy + glyph_offset_y - 1), (cx - 2, cy + glyph_offset_y + 6)], fill=f_color, width=1)
                draw.line([(cx + 2, cy + glyph_offset_y - 1), (cx + 2, cy + glyph_offset_y + 6)], fill=f_color, width=1)
            elif icon in ("refresh-cw", "refresh"):
                f_color = accent or "#10b981"
                draw.arc([(cx - 8, cy + glyph_offset_y - 8), (cx + 8, cy + glyph_offset_y + 8)], start=45, end=315, fill=f_color, width=2)
                draw.polygon([(cx + 4, cy + glyph_offset_y - 11), (cx + 10, cy + glyph_offset_y - 8), (cx + 7, cy + glyph_offset_y - 3)], fill=f_color)
            elif icon in ("headphones", "fone"):
                f_color = accent or "#38bdf8"
                draw.arc([(cx - 18, 16), (cx + 18, 50)], start=180, end=0, fill=f_color, width=3)
                draw.rounded_rectangle([(cx - 21, 32), (cx - 13, 50)], radius=3, fill=f_color)
                draw.rounded_rectangle([(cx + 13, 32), (cx + 21, 50)], radius=3, fill=f_color)
            elif icon in ("speaker", "caixa"):
                f_color = accent or "#f59e0b"
                draw.polygon([(cx - 18, 27), (cx - 9, 27), (cx + 1, 19), (cx + 1, 53), (cx - 9, 45), (cx - 18, 45)], fill=f_color)
                draw.arc([(cx - 4, 22), (cx + 12, 50)], start=300, end=60, fill=f_color, width=3)
                draw.arc([(cx - 4, 14), (cx + 20, 58)], start=300, end=60, fill=f_color, width=3)
            elif icon in ("volume-up", "vol_up"):
                f_color = accent or "#f59e0b"
                draw.polygon([(cx - 18, 27), (cx - 9, 27), (cx + 1, 19), (cx + 1, 53), (cx - 9, 45), (cx - 18, 45)], fill=f_color)
                px, py = cx + 13, 36
                draw.line([(px - 7, py), (px + 7, py)], fill=f_color, width=3)
                draw.line([(px, py - 7), (px, py + 7)], fill=f_color, width=3)
            elif icon in ("volumedown", "volume-down", "vol_down"):
                f_color = accent or "#f59e0b"
                draw.polygon([(cx - 18, 27), (cx - 9, 27), (cx + 1, 19), (cx + 1, 53), (cx - 9, 45), (cx - 18, 45)], fill=f_color)
                px, py = cx + 13, 36
                draw.line([(px - 7, py), (px + 7, py)], fill=f_color, width=3)
            elif icon in ("play-pause", "playpause", "play"):
                f_color = accent or "#22c55e"
                draw.polygon([(cx - 18, 23), (cx - 18, 49), (cx - 3, 36)], fill=f_color)
                draw.rounded_rectangle([(cx + 4, 23), (cx + 8, 49)], radius=1, fill=f_color)
                draw.rounded_rectangle([(cx + 13, 23), (cx + 17, 49)], radius=1, fill=f_color)
            elif icon in ("alert-triangle", "force_quit"):
                f_color = accent or "#ef4444"
                draw.polygon([(cx, cy + glyph_offset_y - 10), (cx - 10, cy + glyph_offset_y + 8), (cx + 10, cy + glyph_offset_y + 8)], outline=f_color, width=2)
                draw.line([(cx, cy + glyph_offset_y - 4), (cx, cy + glyph_offset_y + 2)], fill=f_color, width=2)
                draw.point((cx, cy + glyph_offset_y + 5), fill=f_color)
            elif icon == "info":
                f_color = accent or "#94a3b8"
                draw.ellipse([(cx - 9, cy + glyph_offset_y - 9), (cx + 9, cy + glyph_offset_y + 9)], outline=f_color, width=2)
                draw.line([(cx, cy + glyph_offset_y - 2), (cx, cy + glyph_offset_y + 5)], fill=f_color, width=2)
                draw.point((cx, cy + glyph_offset_y - 5), fill=f_color)
            elif icon == "wifi":
                f_color = accent or "#60a5fa"
                draw.arc([(cx - 11, cy + glyph_offset_y - 7), (cx + 11, cy + glyph_offset_y + 15)], start=215, end=325, fill=f_color, width=2)
                draw.arc([(cx - 7, cy + glyph_offset_y - 3), (cx + 7, cy + glyph_offset_y + 11)], start=215, end=325, fill=f_color, width=2)
                draw.ellipse([(cx - 2, cy + glyph_offset_y + 4), (cx + 2, cy + glyph_offset_y + 8)], fill=f_color)
            elif icon in ("globe", "safari", "web", "sites"):
                f_color = accent or "#ec4899"
                draw.ellipse([(cx - 16, 26), (cx + 16, 58)], outline=f_color, width=2)
                draw.line([(cx - 16, 42), (cx + 16, 42)], fill=f_color, width=2)
                draw.ellipse([(cx - 7, 26), (cx + 7, 58)], outline=f_color, width=2)
            elif icon in ("apps", "grid", "layers"):
                f_color = accent or "#38bdf8"
                for dx, dy in ((-13, 29), (3, 29), (-13, 45), (3, 45)):
                    draw.rounded_rectangle([(cx + dx, dy), (cx + dx + 10, dy + 10)], radius=2, fill=f_color)

        # Se o usuário optou por ocultar o título (DoNotShowTitle), encerra aqui
        if not show_title:
            return img

        # Resolução de Tipografia com fontes reais do macOS
        is_audio_media_key = icon in (
            "headphones", "fone", "speaker", "caixa",
            "volume-up", "vol_up", "volumedown", "volume-down", "vol_down",
            "play-pause", "playpause", "play", "globe", "safari", "web", "sites", "apps", "grid", "layers"
        )
        if is_audio_media_key:
            y_base = cy + 24
            cur_fs = max(13, font_size)
            font_title = self._resolve_font(font_family, cur_fs, bold=True)
            while cur_fs > 10 and draw.textbbox((0, 0), title, font=font_title)[2] > 88:
                cur_fs -= 1
                font_title = self._resolve_font(font_family, cur_fs, bold=True)
            draw.text((cx + 1, y_base + 1), title, fill="#000000", font=font_title, anchor="mm")
            draw.text((cx, y_base), title, fill="#ffffff", font=font_title, anchor="mm")
        else:
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

    def get_rendered_frames_for_page(self, page_id: Optional[str] = None) -> Dict[str, str]:
        """Gera em memória os 15 frames JPEG em base64 idênticos ao hardware para a página solicitada."""
        import io
        import base64

        if not page_id:
            page_id = self.config.get("active_page", "principal")
        page = self.config.get("pages", {}).get(page_id, {})
        keys = page.get("keys", {})

        frames = {}
        for slot in range(1, 16):
            slot_str = str(slot)
            k_data = keys.get(slot_str, {})
            try:
                img = self.render_key_image(k_data)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                frames[slot_str] = f"data:image/jpeg;base64,{b64}"
            except Exception as e:
                pass
        return frames

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

    def set_startup_screen(self, image_path: Optional[str] = None, persist: bool = True) -> bool:
        """
        Sets or flashes the full-screen (854x480) startup / standby image on the physical D6.
        If image_path is None or 'black', a solid pure black image is generated and sent.
        """
        target_w, target_h = 854, 480
        out_dir = Path(__file__).resolve().parent / "studio" / "user_images"
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            if not image_path or image_path == "black":
                canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
                saved_path = out_dir / "startup_screen_black.jpg"
                canvas.save(saved_path, "JPEG", quality=95)
                mode = "black"
                stored_path = ""
            else:
                if not os.path.exists(image_path):
                    print(f"[Engine] Startup screen image does not exist: {image_path}")
                    return False
                img = Image.open(image_path).convert("RGB")
                img_ratio = img.width / img.height
                target_ratio = target_w / target_h
                if img_ratio > target_ratio:
                    new_h = target_h
                    new_w = int(target_h * img_ratio)
                else:
                    new_w = target_w
                    new_h = int(target_w / img_ratio)
                resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                left = (new_w - target_w) // 2
                top = (new_h - target_h) // 2
                canvas = resized.crop((left, top, left + target_w, top + target_h))
                saved_path = out_dir / "startup_screen_custom.jpg"
                canvas.save(saved_path, "JPEG", quality=95)
                mode = "custom"
                stored_path = str(saved_path)

            if persist:
                self.config["startup_screen_mode"] = mode
                self.config["startup_screen_path"] = stored_path
                self.save_config()

            if self.device and self._is_open:
                try:
                    self.device.set_touchscreen_image(str(saved_path))
                    print(f"[Engine] Hardware startup/standby background updated ({mode})")
                except Exception as dev_err:
                    print(f"[Engine] Device set_touchscreen_image error: {dev_err}")
            return True
        except Exception as e:
            print(f"[Engine] Failed to set startup screen: {e}")
            return False

    def reset_startup_screen(self, persist: bool = True) -> bool:
        """Resets the startup screen to pure black, removing any old logo from hardware."""
        return self.set_startup_screen(None, persist=persist)

    def get_startup_screen_info(self) -> Dict[str, Any]:
        """Returns the current startup screen settings."""
        return {
            "mode": self.config.get("startup_screen_mode", "black"),
            "path": self.config.get("startup_screen_path", ""),
            "device_connected": self.is_connected()
        }

    LAUNCH_AGENT_LABEL = "com.hugosilva.ampligame-d6"
    LAUNCH_AGENT_FILE = Path.home() / "Library" / "LaunchAgents" / "com.hugosilva.ampligame-d6.plist"

    def is_autostart_enabled(self) -> bool:
        """Checks if the user LaunchAgent plist exists for automatic startup on login."""
        return self.LAUNCH_AGENT_FILE.exists()

    def set_autostart(self, enable: bool) -> bool:
        """Enables or disables the macOS user LaunchAgent daemon for automatic startup on login."""
        import subprocess

        self.LAUNCH_AGENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        cli_path = Path(__file__).resolve().parent.parent / "run_cli.py"
        repo_dir = Path(__file__).resolve().parent.parent

        plist_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.LAUNCH_AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{cli_path}</string>
        <string>studio</string>
        <string>--no-open</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{repo_dir}</string>
    <key>StandardOutPath</key>
    <string>{Path.home() / "Library" / "Logs" / "ampligame-d6.log"}</string>
    <key>StandardErrorPath</key>
    <string>{Path.home() / "Library" / "Logs" / "ampligame-d6.log"}</string>
</dict>
</plist>
"""
        try:
            if enable:
                with open(self.LAUNCH_AGENT_FILE, "w", encoding="utf-8") as f:
                    f.write(plist_str.strip() + "\n")
                subprocess.run(["launchctl", "load", str(self.LAUNCH_AGENT_FILE)], check=False)
                print(f"[Engine] LaunchAgent created and loaded at {self.LAUNCH_AGENT_FILE}")
            else:
                if self.LAUNCH_AGENT_FILE.exists():
                    subprocess.run(["launchctl", "unload", str(self.LAUNCH_AGENT_FILE)], check=False)
                    self.LAUNCH_AGENT_FILE.unlink(missing_ok=True)
                    print(f"[Engine] LaunchAgent unloaded and removed")
            return True
        except Exception as e:
            print(f"[Engine] Failed to set autostart to {enable}: {e}")
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

    def sync_key(self, key_num: int, force: bool = False, is_pressed: bool = False, page_id: Optional[str] = None, refresh_now: bool = True):
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

            # Rotação base física de 180° do hardware Fifine D6
            rot = int(self.config.get("rotation", 0))
            total_rot = (180 + rot) % 360
            if total_rot != 0:
                img = img.rotate(total_rot)

            # Salva JPEG 4:4:4 cristalino com preenchimento 100% de tela validado fisicamente
            img.save(temp_path, "JPEG", quality=95, subsampling=0, progressive=False, optimize=False)

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

                if res is not None and res < 0:
                    print(f"[Engine] Falha de escrita USB na tecla {key_num} (code {res}). Resetando conexão para auto-reconnect.")
                    self._is_open = False
                    self.device = None
                    return

                if refresh_now and hasattr(self.device, "refresh"):
                    self.device.refresh()
            
            self._displayed_key_hashes[hw_key] = img_hash
        except Exception as e:
            print(f"[Engine] Erro ao sincronizar tecla {key_num}: {e}")
            self._is_open = False
            self.device = None

    def animate_key_press(self, slot_num: int, duration: float = 0.18):
        """Micro-animação tátil de compressão (scale-down 85%) na tela LCD física."""
        if not self.device or not (1 <= slot_num <= 15):
            return

        def _press_thread():
            try:
                # 1. Envia frame de botão pressionado (tamanho reduzido para 82x82 com borda de toque)
                self.sync_key(slot_num, force=True, is_pressed=True, refresh_now=True)
                time.sleep(duration)
                # 2. Retorna ao tamanho original normal
                self.sync_key(slot_num, force=True, is_pressed=False, refresh_now=True)
            except Exception as e:
                print(f"[Engine] Erro na micro-animação da tecla {slot_num}: {e}")

        threading.Thread(target=_press_thread, daemon=True).start()

    def sync_all_keys(self, force: bool = True):
        """Atualiza todas as 15 telas do deck físico com retransmissão completa e segura."""
        if not self.device or not getattr(self, "_is_open", False):
            return

        active_page = self.config.get("active_page", "principal")
        for k in range(1, 16):
            if not self.device or not getattr(self, "_is_open", False):
                break
            self.sync_key(k, force=force, page_id=active_page, refresh_now=False)
            time.sleep(0.01)

        # Atualiza o display no hardware ao final do lote completo
        if self.device and hasattr(self.device, "refresh"):
            with self.lock:
                try:
                    self.device.refresh()
                except Exception as e:
                    print(f"[Engine] Erro ao atualizar display do hardware: {e}")
                    self._is_open = False
                    self.device = None

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

        # Otimização zero-CPU: se nenhuma página tiver linked_app configurado, pula imediatamente sem criar subprocessos
        has_any_link = any(bool(str(p.get("linked_app") or "").strip()) for p in self.config.get("pages", {}).values())
        if not has_any_link:
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

            # Converte com precisão o número da tecla física do hardware para o slot visual correspondente (1 a 15)
            target_slot = self.get_slot_for_hw_key(key_val)

            page_id = self.config.get("active_page", "principal")
            page = self.config.get("pages", {}).get(page_id, {})
            keys_dict = page.get("keys", {})
            key_data = keys_dict.get(str(target_slot))

            print(f"[Hardware Click] Tecla física {key_val} -> Slot visual {target_slot} na página '{page_id}'")

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

    def _get_system_metrics(self) -> Dict[str, str]:
        """Calculates accurate real-time macOS metrics (CPU, RAM, Disk)."""
        metrics = {}
        # 1. CPU (based on load average over available cores)
        try:
            cores = os.cpu_count() or 8
            load = os.getloadavg()[0]
            cpu_pct = min(100, int((load / cores) * 100))
            metrics["cpu"] = f"{cpu_pct}%"
        except Exception:
            metrics["cpu"] = "--%"

        # 2. Disk (free and used space on root partition)
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (1024 ** 3)
            used_pct = int((used / total) * 100)
            metrics["disk"] = f"{free_gb}GB livre"
            metrics["disk_pct"] = f"{used_pct}%"
        except Exception:
            metrics["disk"] = "--GB"

        # 3. RAM (using vm_stat and memory_pressure or sysctl)
        try:
            import subprocess, re
            vm_out = subprocess.check_output(["vm_stat"], timeout=1).decode()
            page_size = 16384
            for line in subprocess.check_output(["sysctl", "hw.pagesize"], timeout=1).decode().splitlines():
                if "hw.pagesize" in line:
                    page_size = int(line.split(":")[1].strip())
            stats = {}
            for line in vm_out.splitlines():
                m = re.match(r'"?([^"]+)"?:\s+(\d+)\.', line.strip())
                if m:
                    stats[m.group(1)] = int(m.group(2))
            free_pages = stats.get("Pages free", 0) + stats.get("Pages speculative", 0) + stats.get("Pages inactive", 0)
            free_bytes = free_pages * page_size
            total_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=1).decode().strip())
            used_bytes = max(0, total_bytes - free_bytes)
            ram_pct = int((used_bytes / total_bytes) * 100)
            metrics["ram"] = f"{ram_pct}%"
        except Exception:
            metrics["ram"] = "--%"

        # 4. Network Ping
        try:
            import subprocess, re
            p_out = subprocess.check_output(["ping", "-c", "1", "-W", "600", "1.1.1.1"], timeout=1).decode()
            m = re.search(r"time=([\d\.]+)\s*ms", p_out)
            if m:
                metrics["ping"] = f"{int(float(m.group(1)))}ms"
            else:
                metrics["ping"] = "OK"
        except Exception:
            metrics["ping"] = "Offline"

        # 5. Output Volume
        try:
            import subprocess
            v_out = subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"], timeout=1).decode().strip()
            metrics["volume"] = f"{v_out}%"
        except Exception:
            metrics["volume"] = "--%"

        return metrics

    def get_recent_unopened_apps(self, count: int = 5) -> List[Dict[str, Any]]:
        """Identifies recently used user apps on macOS that are NOT currently running, guaranteed unique and filled."""
        import subprocess, os

        try:
            ps_out = subprocess.check_output(["ps", "-A", "-o", "comm"], timeout=1).decode()
            running_exes = {os.path.basename(line.strip()).lower() for line in ps_out.splitlines()}
        except Exception:
            running_exes = set()

        cmd = ['mdfind', '-onlyin', '/Applications', 'kMDItemContentType == "com.apple.application-bundle" && kMDItemLastUsedDate > $time.today(-30)']
        try:
            out = subprocess.check_output(cmd, timeout=2).decode().splitlines()
        except Exception:
            out = []

        ignored = {
            "hidden bar", "itsycal", "resetcamera", "cornerswitcher", "finetune",
            "macspace", "finderhelper", "limpar caches", "abrir hub", "antigravity ide",
            "ccxprocess", "coreauth", "safari"
        }

        candidates = []
        seen_names = set()
        seen_paths = set()

        for p in out:
            p = p.strip()
            if not p.endswith(".app") or not os.path.exists(p):
                continue
            if "/utilities/" in p.lower() or "contents/" in p.lower() or "/adobe creative cloud/" in p.lower():
                continue
            app_name = os.path.basename(p)[:-4]
            if app_name.lower() in ignored:
                continue

            clean_key = app_name.lower().replace("adobe", "").strip()
            if clean_key in seen_names or p in seen_paths:
                continue

            # Skip if already running
            if any(clean_key in exe or app_name.lower() in exe for exe in running_exes):
                continue

            try:
                md = subprocess.check_output(['mdls', '-name', 'kMDItemLastUsedDate', p], timeout=1).decode()
                d_str = ""
                for l in md.splitlines():
                    if "kMDItemLastUsedDate" in l and "(null)" not in l:
                        d_str = l.split("=")[1].strip()
                if d_str:
                    candidates.append((d_str, app_name, p))
                    seen_names.add(clean_key)
                    seen_paths.add(p)
            except Exception:
                pass

        candidates.sort(reverse=True)
        selected = candidates[:count]

        # Fallback pool if fewer than count apps were found
        fallback_pool = [
            ("Pearcleaner", "/Applications/Pearcleaner.app"),
            ("OrbStack", "/Applications/OrbStack.app"),
            ("Camo Studio", "/Applications/Camo Studio.app"),
            ("Adobe InDesign 2026", "/Applications/Adobe InDesign 2026/Adobe InDesign 2026.app"),
            ("Adobe Media Encoder 2026", "/Applications/Adobe Media Encoder 2026/Adobe Media Encoder 2026.app"),
            ("The Unarchiver", "/Applications/The Unarchiver.app"),
            ("Adobe Photoshop 2026", "/Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app"),
            ("Adobe Premiere Pro 2026", "/Applications/Adobe Premiere Pro 2026/Adobe Premiere Pro 2026.app"),
            ("Adobe Illustrator", "/Applications/Adobe Illustrator 2026/Adobe Illustrator.app"),
            ("Steam", "/Applications/Steam.app"),
            ("Microsoft Teams", "/Applications/Microsoft Teams.app"),
            ("PixPin", "/Applications/PixPin.app"),
        ]
        if len(selected) < count:
            for fb_name, fb_path in fallback_pool:
                if len(selected) >= count:
                    break
                if not os.path.exists(fb_path):
                    continue
                clean_key = fb_name.lower().replace("adobe", "").strip()
                if clean_key in seen_names or fb_path in seen_paths:
                    continue
                if any(clean_key in exe or fb_name.lower() in exe for exe in running_exes):
                    continue
                seen_names.add(clean_key)
                seen_paths.add(fb_path)
                selected.append(("", fb_name, fb_path))

        # Extract/cache PNG icons using native sips
        result = []
        for _, name, path in selected[:count]:
            clean_name = ''.join(c for c in name if c.isalnum())
            icon_png = f"/tmp/d6_icon_{clean_name}.png"
            if not os.path.exists(icon_png):
                res_dir = os.path.join(path, "Contents", "Resources")
                if os.path.exists(res_dir):
                    icns_files = [f for f in os.listdir(res_dir) if f.endswith(".icns")]
                    target_icns = None
                    for cand in icns_files:
                        cand_l = cand.lower()
                        if any(k in cand_l for k in ("appicon", clean_name.lower(), "icon", "app")):
                            target_icns = cand
                            break
                    if not target_icns and icns_files:
                        target_icns = icns_files[0]
                    if target_icns:
                        try:
                            subprocess.run(
                                ["sips", "-s", "format", "png", os.path.join(res_dir, target_icns), "--out", icon_png, "-Z", "96"],
                                capture_output=True, timeout=2
                            )
                        except Exception:
                            pass

            result.append({
                "name": name,
                "path": path,
                "imagePath": icon_png if os.path.exists(icon_png) else ""
            })

        return result

    def get_open_safari_urls(self) -> List[str]:
        """Obtém as URLs de todas as abas abertas no Safari em tempo real via osascript."""
        import subprocess
        script = '''
tell application "System Events"
    set isRunning to (count of (processes whose name is "Safari")) > 0
end tell
if isRunning then
    tell application "Safari"
        set tabUrls to {}
        repeat with w in windows
            repeat with t in tabs of w
                try
                    set tabUrl to (URL of t as string)
                    if tabUrl is not missing value and tabUrl is not "" then
                        set end of tabUrls to tabUrl
                    end if
                end try
            end repeat
        end repeat
        return tabUrls
    end tell
else
    return {}
end if
'''
        try:
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                return [u.strip() for u in res.stdout.strip().split(", ") if u.strip()]
        except Exception:
            pass
        return []

    def get_favorite_safari_sites(self, count: int = 4) -> List[Dict[str, Any]]:
        """Retorna sites favoritos que NÃO estão atualmente abertos em nenhuma aba do Safari."""
        import urllib.parse
        import urllib.request
        import os

        open_urls = self.get_open_safari_urls()
        open_hosts = []
        for u in open_urls:
            try:
                host = urllib.parse.urlparse(u).netloc.lower()
                if host:
                    open_hosts.append(host)
            except Exception:
                pass

        default_favorites = self.config.get("favorite_sites", [
            {"name": "GitHub", "url": "https://github.com", "domain": "github.com"},
            {"name": "ChatGPT", "url": "https://chatgpt.com", "domain": "chatgpt.com"},
            {"name": "Claude", "url": "https://claude.ai", "domain": "claude.ai"},
            {"name": "Figma", "url": "https://www.figma.com", "domain": "figma.com"},
            {"name": "Notion", "url": "https://www.notion.so", "domain": "notion.so"},
            {"name": "Reddit", "url": "https://www.reddit.com", "domain": "reddit.com"},
            {"name": "YouTube", "url": "https://www.youtube.com", "domain": "youtube.com"},
            {"name": "WhatsApp", "url": "https://web.whatsapp.com", "domain": "whatsapp.com"},
            {"name": "X", "url": "https://x.com", "domain": "x.com"},
            {"name": "LinkedIn", "url": "https://www.linkedin.com", "domain": "linkedin.com"},
            {"name": "Gemini", "url": "https://gemini.google.com", "domain": "gemini.google.com"},
            {"name": "Netflix", "url": "https://www.netflix.com", "domain": "netflix.com"},
            {"name": "Twitch", "url": "https://www.twitch.tv", "domain": "twitch.tv"},
            {"name": "Mercado Livre", "url": "https://www.mercadolivre.com.br", "domain": "mercadolivre.com.br"},
            {"name": "Spotify", "url": "https://open.spotify.com", "domain": "spotify.com"},
            {"name": "Envato", "url": "https://elements.envato.com", "domain": "envato.com"},
            {"name": "Canva", "url": "https://www.canva.com", "domain": "canva.com"},
            {"name": "Stack Overflow", "url": "https://stackoverflow.com", "domain": "stackoverflow.com"},
        ])

        candidates = []
        for site in default_favorites:
            dom = site.get("domain", "").lower()
            if not dom:
                try:
                    dom = urllib.parse.urlparse(site.get("url", "")).netloc.lower()
                except Exception:
                    dom = ""

            # Se o domínio estiver aberto em alguma aba do Safari, NÃO vem para a lista!
            is_open = any(dom in host or host in dom for host in open_hosts)
            if not is_open:
                candidates.append(site)
                if len(candidates) >= count:
                    break

        result = []
        for site in candidates:
            dom = site.get("domain", "")
            icon_path = f"/tmp/d6_fav_{dom.replace('.', '_')}.png"
            if not os.path.exists(icon_path):
                try:
                    fav_url = f"https://www.google.com/s2/favicons?domain={dom}&sz=128"
                    urllib.request.urlretrieve(fav_url, icon_path)
                except Exception:
                    pass

            result.append({
                "name": site.get("name", dom),
                "url": site.get("url", f"https://{dom}"),
                "imagePath": icon_path if os.path.exists(icon_path) else "",
                "domain": dom
            })

        return result

    def refresh_dynamic_row2(self, force: bool = False):
        """Atualiza a Linha 2 (Slots 6 a 10): Slot 6 como botão de alternância e Slots 7-10 como Apps ou Sites."""
        page_id = self.config.get("active_page", "principal")
        page = self.config.get("pages", {}).get(page_id, {})
        if not page.get("has_dynamic_apps") and page_id != "macos_monitor":
            return

        mode = page.get("row2_mode", "apps").lower()
        keys = page.setdefault("keys", {})

        # Slot 6: Botão de Alternância de Modo (APPS <-> SITES)
        slot6_data = keys.get("6", {})
        expected_title = "APPS" if mode == "apps" else "SITES"
        expected_accent = "#38bdf8" if mode == "apps" else "#ec4899"
        expected_icon = "apps" if mode == "apps" else "globe"

        slot6_changed = (
            slot6_data.get("title") != expected_title or
            slot6_data.get("accent") != expected_accent or
            slot6_data.get("icon") != expected_icon or
            slot6_data.get("action", {}).get("type") != "toggle_row2_mode"
        )
        if slot6_changed or force:
            keys["6"] = {
                "title": expected_title,
                "subtitle": "MODO",
                "bg": "#18181b",
                "textColor": "#ffffff",
                "accent": expected_accent,
                "icon": expected_icon,
                "fontSize": 12,
                "bold": True,
                "fontFamily": "Helvetica",
                "showTitle": True,
                "action": {
                    "type": "toggle_row2_mode"
                }
            }
            self.sync_key(6, force=True, page_id=page_id)

        # Slots 7 a 10: 4 itens dinâmicos
        if mode == "sites":
            favorite_sites = self.get_favorite_safari_sites(4)
            for idx in range(4):
                slot_num = 7 + idx
                slot_str = str(slot_num)
                if idx < len(favorite_sites):
                    site_info = favorite_sites[idx]
                    cur_k = keys.get(slot_str, {})
                    is_diff = (
                        cur_k.get("title") != site_info["name"] or
                        cur_k.get("imagePath") != site_info["imagePath"] or
                        cur_k.get("showTitle") is not False or
                        cur_k.get("action", {}).get("target") != site_info["url"]
                    )
                    if is_diff or force:
                        keys[slot_str] = {
                            "title": site_info["name"],
                            "subtitle": "",
                            "bg": "#18181b",
                            "textColor": "#ffffff",
                            "accent": "#ec4899",
                            "fontSize": 11,
                            "bold": True,
                            "fontFamily": "Helvetica",
                            "showTitle": False,
                            "imagePath": site_info["imagePath"],
                            "action": {
                                "type": "open_url",
                                "target": site_info["url"]
                            }
                        }
                        self.sync_key(slot_num, force=True, page_id=page_id)
        else:
            # Modo APPS: 4 apps recentes não abertos
            recent_apps = self.get_recent_unopened_apps(4)
            for idx in range(4):
                slot_num = 7 + idx
                slot_str = str(slot_num)
                if idx < len(recent_apps):
                    app_info = recent_apps[idx]
                    cur_k = keys.get(slot_str, {})
                    is_diff = (
                        cur_k.get("title") != app_info["name"] or
                        cur_k.get("imagePath") != app_info["imagePath"] or
                        cur_k.get("showTitle") is not False or
                        cur_k.get("action", {}).get("target") != app_info["path"]
                    )
                    if is_diff or force:
                        keys[slot_str] = {
                            "title": app_info["name"],
                            "subtitle": "",
                            "bg": "#18181b",
                            "textColor": "#ffffff",
                            "accent": "#38bdf8",
                            "fontSize": 11,
                            "bold": True,
                            "fontFamily": "Helvetica",
                            "showTitle": False,
                            "imagePath": app_info["imagePath"],
                            "action": {
                                "type": "open_app",
                                "target": app_info["path"]
                            }
                        }
                        self.sync_key(slot_num, force=True, page_id=page_id)

    def start_background_telemetry(self):
        """Loop de fundo para métricas dinâmicas (CPU, RAM), auto-troca de perfil e temporizador de inatividade."""
        self.running = True

        def loop():
            while self.running:
                try:
                    now = time.time()

                    # Hotplug / Auto-Reconnect: if not connected, attempt reconnection every 2.0s
                    if not self.is_connected():
                        if now - getattr(self, "_last_reconnect_attempt", 0) >= 2.0:
                            self._last_reconnect_attempt = now
                            if self.connect():
                                print("[Engine] Hotplug detectado: AmpliGame D6 conectado com sucesso!")
                                self.sync_all_keys(force=True)
                        time.sleep(1.0)
                        continue

                    # 0. LED Seguir Modo de Suspensão do macOS (a cada 3.0s)
                    if now - getattr(self, "_last_sleep_check_time", 0) >= 3.0:
                        self._last_sleep_check_time = now
                        follow_mac = self.config.get("led_sleep_follow", True)
                        if follow_mac:
                            mac_off = self.is_mac_screen_off_or_locked()
                            if mac_off:
                                if not self.is_asleep:
                                    self._slept_by_mac_display = True
                                    self.sleep_device(reason="macOS Tela Desligada / Bloqueada")
                                time.sleep(1.0)
                                continue
                            else:
                                if self.is_asleep and getattr(self, "_slept_by_mac_display", False):
                                    self._slept_by_mac_display = False
                                    self.wake_device(reason="macOS Tela Ligada / Desbloqueada")

                    # 1. Temporizador de Inatividade / Economia de Energia (a cada 3.0s)
                    if now - getattr(self, "_last_inactivity_check_time", 0) >= 3.0:
                        self._last_inactivity_check_time = now
                        timeout = int(self.config.get("screen_off_seconds", 0))
                        if timeout > 0:
                            if not self.is_asleep and (now - self._last_activity_time >= timeout):
                                self.sleep_device(reason=f"Inatividade de {timeout}s")
                            elif self.is_asleep and not getattr(self, "_slept_by_mac_display", False):
                                # Se o usuário voltou a interagir ativamente com o Mac (mouse/teclado < 2.0s)
                                if self.get_mac_hid_idle_time() < 2.0:
                                    print("[Engine] Atividade recente de mouse/teclado no macOS -> Acordando teclado")
                                    self.wake_device(reason="Atividade no macOS")

                    # 2. Checagem de auto-troca de perfil pelo app ativo no macOS (a cada 2.5s)
                    if not self.is_asleep and (now - self._last_app_check_time >= 2.5):
                        self._last_app_check_time = now
                        self.check_app_auto_switch()

                    # 3. Métricas de CPU / RAM / Armazenamento / Ping / Volume (a cada 3.0s, apenas se acordado)
                    if not self.is_asleep and (now - self._last_stats_update >= 3.0):
                        self._last_stats_update = now
                        page_id = self.config.get("active_page", "principal")
                        page = self.config.get("pages", {}).get(page_id, {})

                        has_stats_keys = any(
                            isinstance(k_data.get("action"), dict) and k_data["action"].get("type") in ("system_stats", "systemstats")
                            for k_data in page.get("keys", {}).values()
                        )
                        if has_stats_keys:
                            sys_metrics = self._get_system_metrics()
                            for k_str, k_data in page.get("keys", {}).items():
                                act = k_data.get("action", {})
                                if isinstance(act, dict) and act.get("type") in ("system_stats", "systemstats"):
                                    tgt = str(act.get("target", "")).lower()
                                    new_subtitle = None
                                    if tgt == "cpu":
                                        new_subtitle = sys_metrics.get("cpu")
                                    elif tgt == "ram":
                                        new_subtitle = sys_metrics.get("ram")
                                    elif "disk" in tgt or "armazenamento" in tgt or "espaco" in tgt:
                                        new_subtitle = sys_metrics.get("disk")
                                    elif tgt in ("ping", "rede", "net"):
                                        new_subtitle = sys_metrics.get("ping")
                                    elif tgt in ("volume", "vol", "audio"):
                                        new_subtitle = sys_metrics.get("volume")

                                    if new_subtitle and k_data.get("subtitle") != new_subtitle:
                                        k_data["subtitle"] = new_subtitle
                                        self.sync_key(int(k_str), force=True, page_id=page_id)

                    # 4. Linha 2 Dinâmica (Apps Frequentes ou Sites Safari a cada 3.5s)
                    if not self.is_asleep:
                        page_id = self.config.get("active_page", "principal")
                        page = self.config.get("pages", {}).get(page_id, {})
                        if page.get("has_dynamic_apps") or page_id == "macos_monitor":
                            now_dyn = time.time()
                            if now_dyn - getattr(self, "_last_dyn_apps_check", 0) >= 3.5:
                                self._last_dyn_apps_check = now_dyn
                                self.refresh_dynamic_row2()
                except Exception as err:
                    pass
                time.sleep(1.0)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
