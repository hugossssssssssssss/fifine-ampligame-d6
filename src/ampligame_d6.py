#!/usr/bin/env python3
"""
Fifine AmpliGame D6 (StreamDock 293S) Controller & Automation Engine
Driver autônomo e de alta performance via USB/HID para macOS.
Elimina a necessidade do software oficial da Fifine (fifine Control Deck.app),
evita resets de manifest.json, oferece renderização em tempo real nas 15 teclas LCD
e integra diretamente com os scripts locais do workspace.
"""

import sys
import os
import time
import argparse
import threading
from typing import Callable, Optional, Tuple, Dict, Any
from pathlib import Path

# Adiciona o SDK local ao path
SDK_PATH = Path(__file__).resolve().parent.parent / "streamdock-sdk" / "Python-SDK" / "src"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    from StreamDock.DeviceManager import DeviceManager
    from StreamDock.Devices.StreamDock293s import StreamDock293s
    from StreamDock.InputTypes import ButtonKey, EventType
except ImportError as e:
    DeviceManager = None
    StreamDock293s = None


class AmpliGameD6:
    """Controlador de alto nível para o Fifine AmpliGame D6."""

    KEY_SIZE = (85, 85)       # Resolução nativa de cada tecla LCD
    KEY_COUNT = 15            # 15 teclas principais (grade 3x5)
    SECONDARY_KEYS = 3        # 3 botões secundários adicionais

    def __init__(self, auto_open: bool = True):
        if DeviceManager is None:
            raise RuntimeError(
                f"StreamDock SDK não encontrado em {SDK_PATH}. Verifique a instalação."
            )
        self.manager = DeviceManager()
        self.device: Optional[StreamDock293s] = None
        self._key_down_callbacks: Dict[int, list] = {}
        self._key_up_callbacks: Dict[int, list] = {}
        self._any_key_callback: Optional[Callable[[int, int], None]] = None
        self.is_open = False

        if auto_open:
            self.connect()

    def connect(self) -> bool:
        """Descobre e conecta ao AmpliGame D6."""
        devices = self.manager.enumerate()
        if not devices:
            # Tenta novamente após breve delay caso o app da Fifine tenha acabado de ser fechado
            time.sleep(0.3)
            devices = self.manager.enumerate()

        if not devices:
            raise ConnectionError(
                "Nenhum Fifine AmpliGame D6 detectado via USB. Verifique o cabo ou feche o app oficial se estiver bloqueando o dispositivo."
            )

        self.device = devices[0]
        if not self.device.open():
            raise IOError("Falha ao abrir o handle HID do AmpliGame D6.")

        self.device.set_device()
        self.device.wakeScreen()
        self.device.set_key_callback(self._on_raw_key_event)
        self.is_open = True
        return True

    def close(self):
        """Fecha a conexão com o dispositivo com segurança."""
        if self.device and self.is_open:
            try:
                self.device.close()
            except Exception:
                pass
            self.is_open = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def set_brightness(self, percent: int):
        """Ajusta o brilho das telas (0 a 100)."""
        if not self.is_open:
            return
        percent = max(0, min(100, int(percent)))
        self.device.set_brightness(percent)

    def set_rgb(self, r: int, g: int, b: int):
        """Controla a fita de LED RGB da base."""
        if not self.is_open:
            return
        try:
            self.device.set_led_color(r, g, b)
        except Exception as err:
            pass

    def clear(self):
        """Limpa todos os ícones das teclas."""
        if not self.is_open:
            return
        self.device.clearAllIcon()

    def set_key_image(self, key: int, image_or_path) -> bool:
        """
        Define a imagem de uma tecla específica (1 a 18).
        Aceita um caminho de arquivo de imagem ou um objeto PIL.Image.
        """
        if not self.is_open or not self.device:
            return False

        if not (1 <= key <= 18):
            raise ValueError(f"Índice de tecla {key} inválido. Deve ser entre 1 e 18.")

        temp_path = f"/tmp/ampligame_key_{key}.jpg"
        try:
            if isinstance(image_or_path, (str, Path)):
                img = Image.open(str(image_or_path)).convert("RGB")
            elif hasattr(image_or_path, "save"):
                img = image_or_path.convert("RGB")
            else:
                raise TypeError("image_or_path deve ser uma string, Path ou PIL.Image")

            # Redimensiona para resolução ideal do botão mantendo nitidez
            if img.size != self.KEY_SIZE:
                img = img.resize(self.KEY_SIZE, Image.Resampling.LANCZOS)

            img.save(temp_path, "JPEG", quality=95)
            res = self.device.set_key_image(key, temp_path)
            return res == 0
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def render_key(
        self,
        key: int,
        title: str = "",
        subtitle: str = "",
        bg_color: str = "#18181b",
        text_color: str = "#ffffff",
        accent_color: Optional[str] = None,
        font_size: int = 15,
    ) -> bool:
        """Gera e renderiza uma tecla formatada com texto e estilo em tempo real."""
        if Image is None:
            raise ImportError("Pillow não está instalado. Execute: pip install pillow")

        img = Image.new("RGB", self.KEY_SIZE, color=bg_color)
        draw = ImageDraw.Draw(img)

        # Borda/Barra de destaque superior se fornecido accent_color
        if accent_color:
            draw.rectangle([0, 0, self.KEY_SIZE[0], 5], fill=accent_color)
            draw.rounded_rectangle(
                [2, 2, self.KEY_SIZE[0] - 3, self.KEY_SIZE[1] - 3],
                radius=10,
                outline=accent_color,
                width=1,
            )

        # Tenta carregar fonte do sistema ou usa default
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", max(10, font_size - 4))
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = font_title

        cx, cy = self.KEY_SIZE[0] // 2, self.KEY_SIZE[1] // 2

        if title and subtitle:
            draw.text((cx, cy - 8), title, fill=text_color, font=font_title, anchor="mm")
            draw.text((cx, cy + 14), subtitle, fill="#a1a1aa", font=font_sub, anchor="mm")
        elif title:
            # Quebra em múltiplas linhas se houver \n
            draw.text((cx, cy), title, fill=text_color, font=font_title, anchor="mm", align="center")

        return self.set_key_image(key, img)

    def on_key_down(self, key: int, callback: Callable[[int], None]):
        """Registra uma função de callback para o pressionamento de uma tecla específica."""
        self._key_down_callbacks.setdefault(key, []).append(callback)

    def on_key_up(self, key: int, callback: Callable[[int], None]):
        """Registra uma função de callback para a liberação de uma tecla específica."""
        self._key_up_callbacks.setdefault(key, []).append(callback)

    def on_any_key(self, callback: Callable[[int, int], None]):
        """Registra um callback geral: callback(key_index, state [1=press, 0=release])."""
        self._any_key_callback = callback

    def _on_raw_key_event(self, deck, key, state):
        """Disparador interno chamado pelo thread de leitura do HID."""
        key_num = key.value if hasattr(key, "value") else int(key)
        state_num = 1 if state == 1 else 0

        if self._any_key_callback:
            try:
                self._any_key_callback(key_num, state_num)
            except Exception as err:
                print(f"[Callback Error] {err}")

        if state_num == 1:
            for cb in self._key_down_callbacks.get(key_num, []):
                try:
                    cb(key_num)
                except Exception as err:
                    print(f"[Key {key_num} Down Error] {err}")
        else:
            for cb in self._key_up_callbacks.get(key_num, []):
                try:
                    cb(key_num)
                except Exception as err:
                    print(f"[Key {key_num} Up Error] {err}")


def cmd_list(args):
    """Lista detalhes e informações do dispositivo."""
    try:
        with AmpliGameD6() as d6:
            print("\n==============================================")
            print("  Fifine AmpliGame D6 (StreamDock 293S) Conectado")
            print("==============================================")
            print(f"• Fabricante/Modelo:  Fifine / StreamDock 293S")
            print(f"• Vendor ID (VID):    {hex(d6.device.vendor_id)} ({d6.device.vendor_id})")
            print(f"• Product ID (PID):   {hex(d6.device.product_id)} ({d6.device.product_id})")
            print(f"• Número de Série:    {d6.device.serial_number}")
            print(f"• Teclas LCD:         15 principais (3x5) + 3 secundárias")
            print(f"• Resolução por tecla:{AmpliGameD6.KEY_SIZE[0]}x{AmpliGameD6.KEY_SIZE[1]} px")
            print("• Status de Controle: 100% Autônomo e Livre")
            print("==============================================\n")
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)


def cmd_brightness(args):
    """Ajusta o nível de brilho."""
    with AmpliGameD6() as d6:
        d6.set_brightness(args.percent)
        print(f"Brilho ajustado para {args.percent}%.")


def cmd_clear(args):
    """Limpa todas as telas."""
    with AmpliGameD6() as d6:
        d6.clear()
        print("Telas do AmpliGame D6 limpas.")


def cmd_set_key(args):
    """Renderiza texto customizado em uma tecla."""
    with AmpliGameD6() as d6:
        d6.render_key(
            key=args.key,
            title=args.title,
            subtitle=args.subtitle,
            bg_color=args.bg,
            text_color=args.text_color,
            accent_color=args.accent,
            font_size=args.font_size,
        )
        print(f"Tecla {args.key} atualizada com sucesso.")


def cmd_monitor(args):
    """Monitora eventos de pressionamento em tempo real no terminal."""
    print("\n[AmpliGame D6] Monitor de eventos ativado. Pressione botões no hardware para inspecionar.")
    print("Pressione Ctrl+C para sair.\n")

    def log_event(key, state):
        status = "PRESSIONADO (DOWN)" if state == 1 else "LIBERADO (UP)"
        print(f" -> Tecla {key:02d}: {status}")

    with AmpliGameD6() as d6:
        d6.on_any_key(log_event)
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nMonitor encerrado.")


def get_system_stats():
    """Coleta métricas simples de CPU e memória sem depender de libs externas pesadas."""
    try:
        import psutil
        cpu = int(psutil.cpu_percent())
        ram = int(psutil.virtual_memory().percent)
        return cpu, ram
    except Exception:
        # Fallback via os/sysctl se psutil não estiver disponível
        try:
            import subprocess
            load = os.getloadavg()[0]
            cpu = int(min(100, load * 15))
            return cpu, 50
        except Exception:
            return 0, 0


def toggle_macos_mic():
    """Alterna mute/unmute do microfone padrão no macOS via AppleScript."""
    import subprocess
    script = """
    set curVol to input volume of (get volume settings)
    if curVol > 0 then
        set volume input volume 0
        return 0
    else
        set volume input volume 100
        return 100
    end if
    """
    try:
        res = subprocess.check_output(["osascript", "-e", script], text=True).strip()
        return res == "100"
    except Exception:
        return False


def get_macos_mic_status():
    """Verifica se o microfone do macOS está ativo (True) ou mutado (False)."""
    import subprocess
    try:
        res = subprocess.check_output(
            ["osascript", "-e", "return (input volume of (get volume settings))"],
            text=True,
        ).strip()
        return int(res) > 0
    except Exception:
        return True


def check_n8n_status():
    """Verifica se o webhook proxy do n8n está respondendo."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:5678/webhook/docs-proxy", method="OPTIONS")
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return True
    except Exception:
        # Tenta a rota base caso OPTIONS no proxy retorne outro código
        try:
            with urllib.request.urlopen("http://127.0.0.1:5678/", timeout=1.0) as resp:
                return True
        except Exception:
            return False


def send_samsung_tv_cmd(key: str):
    """Envia tecla para o servidor Samsung Smart Remote local se ativo."""
    import urllib.request
    try:
        url = f"http://127.0.0.1:5050/api/remote?key={key}"
        urllib.request.urlopen(url, timeout=1.5)
        return True
    except Exception:
        return False


def cmd_demo(args):
    """Aplica um layout de demonstração com status e atalhos úteis."""
    with AmpliGameD6() as d6:
        d6.clear()
        print("Aplicando layout de demonstração no AmpliGame D6...")

        # Linha 1 (Teclas 1 a 5)
        d6.render_key(1, "SLIDES", "Google", bg_color="#1e1e2e", accent_color="#f59e0b")
        d6.render_key(2, "DOCS", "Google", bg_color="#1e1e2e", accent_color="#3b82f6")
        d6.render_key(3, "SHEETS", "Google", bg_color="#1e1e2e", accent_color="#10b981")
        d6.render_key(4, "DRIVE", "Google", bg_color="#1e1e2e", accent_color="#8b5cf6")
        d6.render_key(5, "PPTX", "Offline", bg_color="#1e1e2e", accent_color="#ef4444")

        # Linha 2 (Teclas 6 a 10)
        d6.render_key(6, "TV POWER", "Samsung", bg_color="#18181b", accent_color="#06b6d4")
        d6.render_key(7, "TV VOL -", "Samsung", bg_color="#18181b", accent_color="#06b6d4")
        d6.render_key(8, "TV VOL +", "Samsung", bg_color="#18181b", accent_color="#06b6d4")
        d6.render_key(9, "TV MUTE", "Samsung", bg_color="#18181b", accent_color="#ec4899")
        d6.render_key(10, "N8N", "Proxy", bg_color="#18181b", accent_color="#f97316")

        # Linha 3 (Teclas 11 a 15)
        d6.render_key(11, "CPU", "--%", bg_color="#0f172a", accent_color="#38bdf8")
        d6.render_key(12, "RAM", "--%", bg_color="#0f172a", accent_color="#a855f7")
        d6.render_key(13, "MIC", "Ativo", bg_color="#14532d", accent_color="#22c55e")
        d6.render_key(14, "BRILHO", "-20%", bg_color="#27272a")
        d6.render_key(15, "BRILHO", "+20%", bg_color="#27272a")

        print("Layout aplicado com sucesso nas 15 teclas!")


def cmd_daemon(args):
    """
    Inicia o daemon de automação com widgets interativos em tempo real:
    - Atualização contínua de CPU e RAM
    - Mute/Unmute do Mac com feedback visual verde/vermelho instantâneo
    - Controle de volume e mute da TV Samsung
    - Monitor do n8n / Docs Proxy
    - Controle de brilho dinâmico das telas
    """
    print("\n=======================================================")
    print("  Fifine AmpliGame D6 - Daemon de Automação Ativo")
    print("=======================================================")
    print("• Controle 100% autônomo via HID USB.")
    print("• Pressione os botões físicos para disparar ações.")
    print("• Pressione Ctrl+C para encerrar o daemon.\n")

    current_brightness = [80]
    running = True

    with AmpliGameD6() as d6:
        d6.set_brightness(current_brightness[0])

        # 1. Desenha o layout base
        d6.render_key(1, "SLIDES", "Google", bg_color="#1e1e2e", accent_color="#f59e0b")
        d6.render_key(2, "DOCS", "Google", bg_color="#1e1e2e", accent_color="#3b82f6")
        d6.render_key(3, "SHEETS", "Google", bg_color="#1e1e2e", accent_color="#10b981")
        d6.render_key(4, "DRIVE", "Google", bg_color="#1e1e2e", accent_color="#8b5cf6")
        d6.render_key(5, "PPTX", "Grade", bg_color="#1e1e2e", accent_color="#ef4444")

        d6.render_key(6, "TV POWER", "Samsung", bg_color="#18181b", accent_color="#06b6d4")
        d6.render_key(7, "TV VOL -", "Samsung", bg_color="#18181b", accent_color="#06b6d4")
        d6.render_key(8, "TV VOL +", "Samsung", bg_color="#18181b", accent_color="#06b6d4")
        d6.render_key(9, "TV MUTE", "Samsung", bg_color="#18181b", accent_color="#ec4899")
        d6.render_key(10, "N8N", "Checando", bg_color="#18181b", accent_color="#f97316")

        d6.render_key(14, "BRILHO -", f"{current_brightness[0]}%", bg_color="#27272a")
        d6.render_key(15, "BRILHO +", f"{current_brightness[0]}%", bg_color="#27272a")

        # Estado inicial do microfone
        mic_active = [get_macos_mic_status()]

        def update_mic_key():
            if mic_active[0]:
                d6.render_key(13, "MIC ON", "Mac", bg_color="#14532d", accent_color="#22c55e")
            else:
                d6.render_key(13, "MUTED", "Mac", bg_color="#7f1d1d", accent_color="#ef4444")

        update_mic_key()

        # Vincula ações de clique
        def on_key_press(key: int):
            print(f"[Ação] Tecla {key} pressionada")

            # Tecla 6: TV Power
            if key == 6:
                send_samsung_tv_cmd("KEY_POWER")
            # Tecla 7: TV Vol Down
            elif key == 7:
                send_samsung_tv_cmd("KEY_VOLDOWN")
            # Tecla 8: TV Vol Up
            elif key == 8:
                send_samsung_tv_cmd("KEY_VOLUP")
            # Tecla 9: TV Mute
            elif key == 9:
                send_samsung_tv_cmd("KEY_MUTE")
            # Tecla 10: Teste N8N
            elif key == 10:
                ok = check_n8n_status()
                color = "#10b981" if ok else "#ef4444"
                text = "ONLINE" if ok else "OFFLINE"
                d6.render_key(10, "N8N", text, bg_color="#18181b", accent_color=color)
            # Tecla 13: Mic Toggle
            elif key == 13:
                new_state = toggle_macos_mic()
                mic_active[0] = new_state
                update_mic_key()
            # Tecla 14: Brilho -
            elif key == 14:
                current_brightness[0] = max(10, current_brightness[0] - 20)
                d6.set_brightness(current_brightness[0])
                d6.render_key(14, "BRILHO -", f"{current_brightness[0]}%", bg_color="#27272a")
                d6.render_key(15, "BRILHO +", f"{current_brightness[0]}%", bg_color="#27272a")
            # Tecla 15: Brilho +
            elif key == 15:
                current_brightness[0] = min(100, current_brightness[0] + 20)
                d6.set_brightness(current_brightness[0])
                d6.render_key(14, "BRILHO -", f"{current_brightness[0]}%", bg_color="#27272a")
                d6.render_key(15, "BRILHO +", f"{current_brightness[0]}%", bg_color="#27272a")

        for k in range(1, 19):
            d6.on_key_down(k, on_key_press)

        # Thread de atualização de widgets em tempo real (CPU, RAM, N8N Status)
        def widget_loop():
            last_n8n_check = 0
            while running:
                try:
                    cpu, ram = get_system_stats()
                    d6.render_key(11, "CPU", f"{cpu}%", bg_color="#0f172a", accent_color="#38bdf8")
                    d6.render_key(12, "RAM", f"{ram}%", bg_color="#0f172a", accent_color="#a855f7")

                    now = time.time()
                    if now - last_n8n_check > 15:
                        last_n8n_check = now
                        ok = check_n8n_status()
                        color = "#10b981" if ok else "#ef4444"
                        text = "ONLINE" if ok else "OFFLINE"
                        d6.render_key(10, "N8N", text, bg_color="#18181b", accent_color=color)
                except Exception as err:
                    print(f"[Widget Loop Error] {err}")
                time.sleep(2.0)

        t = threading.Thread(target=widget_loop, daemon=True)
        t.start()

        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            running = False
            print("\nDaemon finalizado.")


def cmd_studio(args):
    """Inicia o servidor e abre a interface web Studio Pro."""
    from d6_studio_server import run_studio
    run_studio(auto_open=not args.no_open)


def main():
    parser = argparse.ArgumentParser(description="Fifine AmpliGame D6 Autonomous CLI Controller")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="Lista dados de hardware do AmpliGame D6")

    # brightness
    p_bright = subparsers.add_parser("brightness", help="Ajusta o brilho da tela (0-100)")
    p_bright.add_argument("percent", type=int, help="Percentual de 0 a 100")

    # clear
    subparsers.add_parser("clear", help="Limpa todas as telas LCD")

    # set-key
    p_key = subparsers.add_parser("set-key", help="Define texto e visual de uma tecla")
    p_key.add_argument("--key", "-k", type=int, required=True, help="Número da tecla (1 a 18)")
    p_key.add_argument("--title", "-t", type=str, default="", help="Título principal")
    p_key.add_argument("--subtitle", "-s", type=str, default="", help="Subtítulo menor")
    p_key.add_argument("--bg", type=str, default="#18181b", help="Cor de fundo (#hex)")
    p_key.add_argument("--text-color", type=str, default="#ffffff", help="Cor do texto (#hex)")
    p_key.add_argument("--accent", type=str, default=None, help="Cor da borda/destaque (#hex)")
    p_key.add_argument("--font-size", type=int, default=15, help="Tamanho da fonte")

    # monitor
    subparsers.add_parser("monitor", help="Monitora eventos de clique em tempo real")

    # demo
    subparsers.add_parser("demo", help="Aplica layout de demonstração integrado ao workspace")

    # daemon
    subparsers.add_parser("daemon", help="Inicia o serviço interativo com widgets e ações nos botões")

    # studio / ui
    p_studio = subparsers.add_parser("studio", help="Inicia a interface visual Studio Pro no navegador")
    p_studio.add_argument("--no-open", action="store_true", help="Não abre automaticamente o navegador")

    p_ui = subparsers.add_parser("ui", help="Atalho para 'studio'")
    p_ui.add_argument("--no-open", action="store_true", help="Não abre automaticamente o navegador")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "brightness": cmd_brightness,
        "clear": cmd_clear,
        "set-key": cmd_set_key,
        "monitor": cmd_monitor,
        "demo": cmd_demo,
        "daemon": cmd_daemon,
        "studio": cmd_studio,
        "ui": cmd_studio,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
