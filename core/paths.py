"""Filesystem-path helpers shared by the Workspaces and Duplicates tabs."""
import os
from pathlib import Path


def is_broad_scan_root(path: str) -> bool:
    """True when ``path`` is a filesystem root or the user's home directory.

    Scanning either one walks a whole drive (or a whole home folder) in
    ``scan_repos``: it is slow, it has no cancel button in the UI, and it
    flags any directory named ``build``/``bin``/``obj``/``venv`` anywhere
    under it, including places that are not part of any project. A normal
    development folder — even one directly under home, like
    ``~/Development`` — is NOT broad: only the exact root and the exact
    home directory count, so this never false-positives on a real dev
    folder. Relative and empty paths are not broad either; they are
    simply invalid scan roots, and the folder picker never produces them.
    """
    if not path or not os.path.isabs(path):
        return False
    resolved = Path(os.path.realpath(path))
    if str(resolved) == resolved.anchor:
        return True
    home = Path(os.path.realpath(str(Path.home())))
    return os.path.normcase(str(resolved)) == os.path.normcase(str(home))
