import argparse
import sys
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

    def test_packaged_binaries_are_smoke_tested_before_distribution(self):
        windows = Path("agent/packaging/windows/Build-WindowsInstaller.ps1").read_text(encoding="utf-8")
        macos = Path("agent/packaging/macos/build-binary.sh").read_text(encoding="utf-8")
        self.assertIn("Packaged agent command-line smoke test failed", windows)
        self.assertIn("--hidden-import onyx_agent.windows_service", windows)
        self.assertIn("Packaged Windows service dispatcher smoke test failed", windows)
        self.assertIn("Packaged agent command-line smoke test failed", macos)

    def test_windows_ci_installs_and_starts_the_built_msi(self):
        workflow = Path(".github/workflows/endpoint-agent-packages.yml").read_text(encoding="utf-8")
        self.assertIn("Install and exercise Windows service", workflow)
        self.assertIn("Get-Service OnyxEndpointAgent", workflow)
        self.assertIn("expected Running", workflow)

    def test_macos_assembly_does_not_reference_missing_installer_directory(self):
        workflow = Path(".github/workflows/endpoint-agent-packages.yml").read_text(encoding="utf-8")
        self.assertNotIn("cd installers", workflow)

    def test_macos_release_requires_notarization_and_gatekeeper_verification(self):
        workflow = Path(".github/workflows/endpoint-agent-packages.yml").read_text(encoding="utf-8")
        build = Path("agent/packaging/macos/build-universal-dmg.sh").read_text(encoding="utf-8")
        self.assertIn("Require Apple distribution credentials", workflow)
        self.assertGreaterEqual(build.count("xcrun notarytool submit"), 3)
        self.assertGreaterEqual(build.count("xcrun stapler validate"), 3)
        self.assertIn("spctl --assess --type install", build)
        self.assertIn("spctl --assess --type execute", build)
        self.assertIn("spctl --assess --type open", build)

    def test_windows_installer_starts_service_and_includes_desktop(self):
        wix = Path("agent/packaging/windows/OnyxAgent.wxs").read_text(encoding="utf-8")
        self.assertIn('Start="auto"', wix)
        self.assertIn('Start="install"', wix)
        self.assertIn("OnyxDesktopExe", wix)
        self.assertIn("LaunchOnyxDesktop", wix)
        self.assertIn("Windows\\CurrentVersion\\Run", wix)

    def test_cli_parses_arguments_before_dispatch(self):
        marker = argparse.Namespace(called=False)

        def fake_status(_):
            marker.called = True
            return 0

        with patch.object(sys, "argv", ["onyx-agent", "status"]), patch.object(cli, "status", fake_status):
            self.assertEqual(cli.main(), 0)
        self.assertTrue(marker.called)


if __name__ == "__main__":
    unittest.main()
