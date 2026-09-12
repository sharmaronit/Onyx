import argparse
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.onyx_agent import __main__ as cli


class AgentInstallLifecycleTests(unittest.TestCase):
    def test_macos_uses_enrollment_api_platform_name(self):
        with patch.object(cli.platform, "system", return_value="Darwin"):
            self.assertEqual(cli.platform_name(), "macOS")

    def test_windows_uses_expected_enrollment_api_platform_name(self):
        with patch.object(cli.platform, "system", return_value="Windows"):
            self.assertEqual(cli.platform_name(), "Windows")

    def test_windows_requires_elevation_before_token_is_used(self):
        with patch.object(cli.platform, "system", return_value="Windows"), patch(
            "ctypes.windll.shell32.IsUserAnAdmin", return_value=0
        ), self.assertRaises(PermissionError):
            cli.require_administrator()

    def test_macos_installer_waits_for_enrollment_before_loading_daemon(self):
        script = Path("agent/packaging/macos/scripts/postinstall").read_text(encoding="utf-8")
        self.assertNotIn("launchctl bootstrap", script)
        self.assertIn("onyx-agent enroll", script)


if __name__ == "__main__":
    unittest.main()
