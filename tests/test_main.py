"""Tests for main.py startup helpers."""

from unittest.mock import patch

import main


class TestGetWindowKwargs:
    def test_uses_dialog_style_on_macos(self):
        with patch.object(main.sys, "platform", "darwin"), patch.object(main.Window, "WINDOW_STYLE_DIALOG", "dialog", create=True):
            kwargs = main._get_window_kwargs()
        assert kwargs["resizable"] is True
        assert kwargs["style"] == "dialog"

    def test_uses_default_style_off_macos(self):
        with patch.object(main.sys, "platform", "win32"):
            kwargs = main._get_window_kwargs()
        assert kwargs == {"resizable": True}
