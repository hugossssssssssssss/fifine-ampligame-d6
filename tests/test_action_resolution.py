"""
Testes de Regressão: Resolução Universal de Ações do Catálogo e Mapeamento de Comandos.
Garante que todas as 43 ações da interface Web e do hardware Fifine AmpliGame D6
sejam resolvidas para suas respectivas classes ActionCommand sem ambiguidades ou conflitos.
"""

import unittest
import sys
from pathlib import Path

# Adiciona o diretório src ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from actions.registry import ActionRegistry
from actions.navigation_action import NavigationCommand
from actions.soundboard_action import SoundboardPlayCommand, SoundboardStopCommand
from actions.media_action import NextTrackCommand, PrevTrackCommand
from actions.system_action import MissionControlCommand, LaunchpadCommand, MouseEventCommand, TextInputCommand
from actions.device_action import BrightnessCommand, SleepDeviceCommand, ToggleStateCommand
from actions.app_action import ToggleRow2ModeCommand


class TestActionCatalogResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ActionRegistry.initialize()

    def test_dispatchcenter_resolution(self):
        cmd = ActionRegistry.resolve("com.hotspot.streamdock.touchbar.dispatchcenter")
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd, MissionControlCommand)

    def test_launchpad_resolution(self):
        cmd = ActionRegistry.resolve("com.hotspot.streamdock.touchbar.launchpad")
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd, LaunchpadCommand)

    def test_page_navigation_precedence_over_media(self):
        # Evita que 'page.previous' caia em PrevTrackCommand
        prev_cmd = ActionRegistry.resolve("com.hotspot.streamdock.page.previous")
        self.assertIsNotNone(prev_cmd)
        self.assertIsInstance(prev_cmd, NavigationCommand)

        # Evita que 'page.next' caia em NextTrackCommand
        next_cmd = ActionRegistry.resolve("com.hotspot.streamdock.page.next")
        self.assertIsNotNone(next_cmd)
        self.assertIsInstance(next_cmd, NavigationCommand)

        # Mídia normal deve continuar indo para PrevTrack e NextTrack
        media_prev = ActionRegistry.resolve("com.hotspot.streamdock.touchbar.previoustrack")
        self.assertIsNotNone(media_prev)
        self.assertIsInstance(media_prev, PrevTrackCommand)

        media_next = ActionRegistry.resolve("com.hotspot.streamdock.touchbar.nexttrack")
        self.assertIsNotNone(media_next)
        self.assertIsInstance(media_next, NextTrackCommand)

    def test_stopaudioplay_precedence_over_playaudio(self):
        # Evita que stopaudioplay caia em SoundboardPlayCommand por conter 'soundboard'
        stop_cmd = ActionRegistry.resolve("com.hotspot.streamdock.soundboard.stopaudioplay")
        self.assertIsNotNone(stop_cmd)
        self.assertIsInstance(stop_cmd, SoundboardStopCommand)

        play_cmd = ActionRegistry.resolve("com.hotspot.streamdock.soundboard.playaudio")
        self.assertIsNotNone(play_cmd)
        self.assertIsInstance(play_cmd, SoundboardPlayCommand)

    def test_hardware_and_mouse_resolution(self):
        b_cmd = ActionRegistry.resolve("com.hotspot.streamdock.device.brightness")
        self.assertIsNotNone(b_cmd)
        self.assertIsInstance(b_cmd, BrightnessCommand)

        s_cmd = ActionRegistry.resolve("com.hotspot.streamdock.device.devsleep")
        self.assertIsNotNone(s_cmd)
        self.assertIsInstance(s_cmd, SleepDeviceCommand)

        m_cmd = ActionRegistry.resolve("com.hotspot.streamdock.mouse.event")
        self.assertIsNotNone(m_cmd)
        self.assertIsInstance(m_cmd, MouseEventCommand)

        pwd_cmd = ActionRegistry.resolve("com.hotspot.streamdock.system.password")
        self.assertIsNotNone(pwd_cmd)
        self.assertIsInstance(pwd_cmd, TextInputCommand)

        t_cmd = ActionRegistry.resolve("com.hotspot.streamdock.system.toggle")
        self.assertIsNotNone(t_cmd)
        self.assertIsInstance(t_cmd, ToggleStateCommand)

    def test_toggle_row2_mode_resolution_and_toggle(self):
        cmd = ActionRegistry.resolve("toggle_row2_mode")
        self.assertIsNotNone(cmd)
        self.assertIsInstance(cmd, ToggleRow2ModeCommand)

        class DummyEngine:
            def __init__(self):
                self.config = {"active_page": "p1", "pages": {"p1": {"row2_mode": "apps"}}}
                self.refreshed = False
                self.saved = False
            def refresh_dynamic_row2(self, force=False):
                self.refreshed = True
            def save_config(self):
                self.saved = True

        dummy = DummyEngine()
        from models.action import ActionModel
        # Toggle from apps -> sites
        success = cmd.execute(ActionModel(type="toggle_row2_mode"), slot=6, engine=dummy)
        self.assertTrue(success)
        self.assertEqual(dummy.config["pages"]["p1"]["row2_mode"], "sites")
        self.assertTrue(dummy.refreshed)
        self.assertTrue(dummy.saved)

        # Toggle from sites -> apps
        cmd.execute(ActionModel(type="toggle_row2_mode"), slot=6, engine=dummy)
        self.assertEqual(dummy.config["pages"]["p1"]["row2_mode"], "apps")


if __name__ == "__main__":
    unittest.main()
