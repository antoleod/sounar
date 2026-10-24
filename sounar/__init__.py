"""Sounar (sound + arrange): several speakers arranged into one system, switched as presets."""

__version__ = "0.1.0"


class SounarError(Exception):
    """Something the user can fix; the message is shown as is (`sounar: <message>`)."""
