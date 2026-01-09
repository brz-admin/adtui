"""ADTUI - Active Directory Terminal User Interface."""

# Version is read from package metadata (set in pyproject.toml)
try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("adtui")
    except PackageNotFoundError:
        # Package not installed (development mode)
        __version__ = "0.0.0-dev"
except ImportError:
    # Python < 3.8 fallback
    __version__ = "0.0.0-dev"

__author__ = "Brz"
__email__ = "brz@brznet.fr"

from .adtui import ADTUI, main

__all__ = ["ADTUI", "main", "__version__"]
