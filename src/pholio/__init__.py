"""Pholio — Photo album PDF generator."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("pholio")
except PackageNotFoundError:
    __version__ = "dev"
