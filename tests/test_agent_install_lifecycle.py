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

    def test_macos_installer_starts_idle_daemon_for_desktop_enrollment(self):
        script = Path("agent/packaging/macos/scripts/postinstall").read_text(encoding="utf-8")
        self.assertIn("launchctl bootstrap", script)
        self.assertIn("Open Onyx Agent", script)

    def test_windows_installer_starts_idle_service_and_includes_desktop(self):
        wix = Path("agent/packaging/windows/OnyxAgent.wxs").read_text(encoding="utf-8")
        self.assertIn('Start="install"', wix)
        self.assertIn("OnyxDesktopExe", wix)
        self.assertIn("LaunchOnyxDesktop", wix)
        self.assertIn("Windows\\CurrentVersion\\Run", wix)


if __name__ == "__main__":
    unittest.main()
