import unittest
import os
import sys

# Ensure src is on sys.path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from actions.media_action import _get_volume_step, ToggleAudioOutputCommand, SmartPlayPauseCommand
from models.action import ActionModel
from d6_engine import D6Engine


class MockEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self.is_connected_flag = False

    def is_connected(self):
        return self.is_connected_flag


class TestActionCustomization(unittest.TestCase):

    def test_volume_step_resolution_default(self):
        act = ActionModel(type="volume_up", target="system")
        step = _get_volume_step(act, None)
        self.assertEqual(step, 6.25)

    def test_volume_step_resolution_from_engine_config(self):
        act = ActionModel(type="volume_up", target="system")
        engine = MockEngine({"volume_step": 10.0})
        step = _get_volume_step(act, engine)
        self.assertEqual(step, 10.0)

    def test_volume_step_resolution_from_action_override(self):
        act = ActionModel(type="volume_up", target="system", raw={"step": 2.5})
        engine = MockEngine({"volume_step": 10.0})
        step = _get_volume_step(act, engine)
        self.assertEqual(step, 2.5)

    def test_toggle_audio_device_resolution(self):
        cmd = ToggleAudioOutputCommand()
        act = ActionModel(
            type="toggle_audio",
            target="system",
            raw={"device_a": "Minhas Caixas Externas", "device_b": "AirPods Pro"}
        )
        self.assertEqual(act.raw.get("device_a"), "Minhas Caixas Externas")
        self.assertEqual(act.raw.get("device_b"), "AirPods Pro")

    def test_smart_play_pause_custom_fallback(self):
        act = ActionModel(
            type="smart_play_pause",
            target="system",
            raw={"fallback_url": "https://music.youtube.com/playlist?list=MY_LIST", "auto_shuffle": False}
        )
        self.assertEqual(act.raw.get("fallback_url"), "https://music.youtube.com/playlist?list=MY_LIST")
        self.assertFalse(act.raw.get("auto_shuffle"))

    def test_blocked_sites_filtering(self):
        engine = D6Engine()
        engine.config["favorite_sites"] = [
            {"name": "GitHub", "url": "https://github.com", "domain": "github.com"},
            {"name": "Reddit", "url": "https://reddit.com", "domain": "reddit.com"},
            {"name": "YouTube", "url": "https://youtube.com", "domain": "youtube.com"}
        ]
        engine.config["blocked_sites"] = ["reddit.com"]

        favorites = engine.get_favorite_safari_sites(count=5)
        domains = [f.get("domain") for f in favorites]
        self.assertNotIn("reddit.com", domains)
        self.assertIn("github.com", domains)

    def test_blocked_apps_filtering(self):
        engine = D6Engine()
        engine.config["blocked_apps"] = ["Safari", "Calculator", "Notas"]
        # get_recent_unopened_apps checks user_blocked
        recent = engine.get_recent_unopened_apps(count=5)
        recent_names_lower = [a.get("name", "").lower() for a in recent]
        for blocked in engine.config["blocked_apps"]:
            self.assertNotIn(blocked.lower(), recent_names_lower)


if __name__ == "__main__":
    unittest.main()
