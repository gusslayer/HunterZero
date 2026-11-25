"""Guard the deployment contract for display, power button, and updates."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    """Check that installer scripts stay consistent with the GPi hardware."""

    def test_config_leaves_power_gpios_to_the_dedicated_service(self):
        """Do not let DT overlays claim GPIO 26/27 before the power service."""
        config = (ROOT / "deploy" / "config.txt").read_text(encoding="utf-8")
        active_lines = [
            line.strip()
            for line in config.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertFalse(
            [line for line in active_lines if line.startswith("dtoverlay=gpio-shutdown")]
        )
        self.assertFalse(
            [line for line in active_lines if line.startswith("dtoverlay=gpio-led")]
        )
        self.assertIn("hunterzero-poweroff.service", config)

    def test_installer_installs_gpiod_and_the_poweroff_service(self):
        """Require the GPIO tools and both systemd units after installation."""
        installer = (ROOT / "deploy" / "install.sh").read_text(encoding="utf-8")
        self.assertIn("gpiod", installer)
        self.assertIn("/usr/local/bin/hunterzero-poweroff", installer)
        self.assertIn("/etc/systemd/system/hunterzero-poweroff.service", installer)

    def test_poweroff_script_waits_for_gpio26_falling_edge(self):
        """Keep GPIO 27 high and shut down only on the physical button edge."""
        script = (ROOT / "deploy" / "hunterzero-poweroff.sh").read_text(encoding="utf-8")
        self.assertIn('gpioset -c "$GPIO_CHIP" -C "$CONSUMER" "$POWER_ENABLE_LINE=1"', script)
        self.assertIn("-e falling", script)
        self.assertIn("-n 1", script)
        self.assertIn('"$SHUTDOWN_BIN" -h now', script)

    def test_update_reinstalls_the_poweroff_service(self):
        """An update must not leave the Pi without a GPIO power-button watcher."""
        update = (ROOT / "deploy" / "update.sh").read_text(encoding="utf-8")
        self.assertIn("/usr/local/bin/hunterzero-poweroff", update)
        self.assertIn("/etc/systemd/system/hunterzero-poweroff.service", update)
        self.assertIn("systemctl enable --now hunterzero-poweroff.service", update)

    def test_poweroff_service_restarts_even_after_clean_exit(self):
        """Keep monitoring the button if gpiomon stops for any reason."""
        unit = (ROOT / "deploy" / "hunterzero-poweroff.service").read_text(encoding="utf-8")
        self.assertIn("Restart=always", unit)

    def test_update_uses_visible_progress_without_interactive_prompts(self):
        """Force git progress and disable credential prompts from the kiosk."""
        update = (ROOT / "deploy" / "update.sh").read_text(encoding="utf-8")
        self.assertIn("GIT_TERMINAL_PROMPT=0", update)
        self.assertIn("pull --ff-only --progress", update)
        gui_branch = update.split('if [[ "${HUNTERZERO_UPDATE_GUI:-0}" == "1" ]]', 1)[1]
        gui_branch = gui_branch.split("fi", 1)[0]
        self.assertIn("exit 0", gui_branch)
        self.assertNotIn("\n sudo ", gui_branch)


if __name__ == "__main__":
    unittest.main()
