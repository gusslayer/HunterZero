"""Verify that display failures explain the required KMS devices and permissions."""

import unittest
from unittest.mock import patch

from core.screen import _candidate_drivers, _video_device_diagnostics


class DisplayDiagnosticsTests(unittest.TestCase):
    """Cover display-driver selection and actionable hardware diagnostics."""

    def test_forced_kms_keeps_framebuffer_as_only_fallback(self):
        """Do not hide a physical-display failure by silently selecting dummy."""
        self.assertEqual(_candidate_drivers("kmsdrm"), ["kmsdrm", "fbcon"])

    @patch("core.screen.glob.glob", return_value=[])
    def test_reports_missing_kms_and_framebuffer_nodes(self, _glob):
        """Point to kernel display setup when neither DRM nor fbdev is present."""
        message = _video_device_diagnostics({"kmsdrm": "EGL not initialized"})
        self.assertIn("no se detectan /dev/dri/* ni /dev/fb*", message)
        self.assertIn("kernel no expuso /dev/dri/card*", message)

    @patch("core.screen.os.access", return_value=False)
    @patch(
        "core.screen.glob.glob",
        side_effect=lambda pattern: ["/dev/dri/card0"] if pattern.endswith("card*") else [],
    )
    def test_reports_inaccessible_drm_node(self, _glob, _access):
        """Identify group permissions when DRM exists but the service cannot use it."""
        message = _video_device_diagnostics({"kmsdrm": "EGL not initialized"})
        self.assertIn("video/render", message)
