"""Platform Service - Cross-platform path and environment utilities."""

import os
import sys
from pathlib import Path
from typing import Optional


class PlatformService:
    """Service for platform-specific paths and operations."""

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows."""
        return sys.platform == "win32"

    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS."""
        return sys.platform == "darwin"

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux."""
        return sys.platform.startswith("linux")

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory path.

        Returns:
            - Windows: %APPDATA%\\adtui
            - macOS/Linux: ~/.config/adtui
        """
        if cls.is_windows():
            base = os.environ.get("APPDATA")
            if base:
                return Path(base) / "adtui"
            return Path.home() / "AppData" / "Roaming" / "adtui"
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                return Path(xdg_config) / "adtui"
            return Path.home() / ".config" / "adtui"

    @classmethod
    def get_data_dir(cls) -> Path:
        """Get the data/install directory path.

        Returns:
            - Windows: %LOCALAPPDATA%\\adtui
            - macOS/Linux: ~/.local/share/adtui
        """
        if cls.is_windows():
            base = os.environ.get("LOCALAPPDATA")
            if base:
                return Path(base) / "adtui"
            return Path.home() / "AppData" / "Local" / "adtui"
        else:
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                return Path(xdg_data) / "adtui"
            return Path.home() / ".local" / "share" / "adtui"

    @classmethod
    def get_venv_dir(cls) -> Path:
        """Get the virtual environment directory path."""
        return cls.get_data_dir() / "venv"

    @classmethod
    def get_pip_path(cls) -> Optional[Path]:
        """Get the pip executable path in the venv.

        Returns:
            Path to pip executable, or None if not found.
        """
        venv_dir = cls.get_venv_dir()

        if cls.is_windows():
            pip_path = venv_dir / "Scripts" / "pip.exe"
            if pip_path.exists():
                return pip_path
            pip_path = venv_dir / "Scripts" / "pip"
            if pip_path.exists():
                return pip_path
        else:
            pip_path = venv_dir / "bin" / "pip"
            if pip_path.exists():
                return pip_path

        return None

    @classmethod
    def get_python_path(cls) -> Optional[Path]:
        """Get the Python executable path in the venv.

        Returns:
            Path to python executable, or None if not found.
        """
        venv_dir = cls.get_venv_dir()

        if cls.is_windows():
            python_path = venv_dir / "Scripts" / "python.exe"
            if python_path.exists():
                return python_path
        else:
            python_path = venv_dir / "bin" / "python"
            if python_path.exists():
                return python_path

        return None

    @classmethod
    def get_legacy_config_path(cls, filename: str = "config.ini") -> Optional[Path]:
        """Get legacy config path (Unix only).

        Returns:
            Path to legacy config file on Unix, None on Windows.
        """
        if cls.is_windows():
            return None
        return Path.home() / f".adtui_{filename}"
