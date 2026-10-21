import os
from pathlib import Path
from send2trash import send2trash

def safe_delete(path: str) -> bool:
    """
    Moves the given file or directory to the OS Recycle Bin/Trash.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(path):
        return False

    try:
        send2trash(path)
        return True
    except Exception as e:
        print(f"Failed to trash {path}: {e}")
        return False

def empty_directory_contents(path: str) -> tuple[int, int]:
    """
    Moves all contents of a directory to the Recycle Bin, but keeps the root directory.
    Returns (success_count, fail_count).
    """
    if not os.path.exists(path) or not os.path.isdir(path):
        return 0, 0

    success_count = 0
    fail_count = 0

    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        try:
            send2trash(full_path)
            success_count += 1
        except Exception:
            fail_count += 1

    return success_count, fail_count

def _protected_subtrees() -> list:
    """
    Absolute directories whose entire subtree must never be a deletion target.
    Non-absolute entries are dropped so the same list works on every OS.

    Note: the Windows directory itself is NOT in this list — it is refused
    exactly (see _is_windows_dir) so that its known cache subfolders
    (C:\\Windows\\Temp, C:\\Windows\\SoftwareDistribution\\...) stay cleanable.
    """
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    subtrees = []
    if windir and os.path.isabs(windir):
        for sub in ("System32", "SysWOW64", "WinSxS", "Fonts"):
            subtrees.append(os.path.join(windir, sub))
    subtrees.extend(["/System", "/usr", "/bin", "/sbin", "/etc", "/var", "/Library"])
    return [d for d in subtrees if os.path.isabs(d)]

def _is_windows_dir(norm_target: str) -> bool:
    """True when the target IS the Windows directory itself (exact match)."""
    windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if not windir or not os.path.isabs(windir):
        return False
    return norm_target == os.path.normcase(windir)

def is_safe_deletion_target(path: str) -> bool:
    """
    Decides whether `path` may be cleaned by hard_delete_directory_contents.

    The path is first normalised to an absolute, symlink-resolved path; the
    guards are then applied to that resolved path:

    - it must be absolute in the first place (relative input is refused even
      if it would resolve somewhere deep)
    - it must be an existing directory
    - it must not be a filesystem root ("/", "C:\\", ...)
    - it must not be the user's home directory
    - it must not be (or sit inside) a protected system directory
      (Windows dir itself, System32/SysWOW64/WinSxS/Fonts,
      /System, /usr, /bin, /sbin, /etc, /var, /Library).
      Known cache subfolders of the Windows dir (C:\\Windows\\Temp,
      C:\\Windows\\SoftwareDistribution\\...) stay cleanable.
    - it must be at least 2 components deep below the filesystem anchor,
      e.g. "/Users/name/.npm" or "C:\\Windows\\Temp"

    The depth rule exists so that a shallow slip (like a "C:\\Temp" fallback
    or a drive root) can never become a deletion target.
    """
    if not path:
        return False

    # Refuse relative paths outright: a missing env var (for example
    # LOCALAPPDATA) can otherwise turn a cache path into a CWD-relative
    # deletion. All legitimate callers pass absolute paths.
    if not os.path.isabs(path):
        return False

    target = os.path.realpath(path)
    if not os.path.isdir(target):
        return False

    p = Path(target)
    anchor = p.anchor

    # Never the filesystem root itself.
    if str(p) == anchor:
        return False

    # Never the user's home directory.
    if os.path.normcase(str(p)) == os.path.normcase(str(Path.home())):
        return False

    # Never the Windows directory itself (exact match only; its known cache
    # subfolders stay cleanable, critical subdirs are refused below).
    norm_target = os.path.normcase(str(p))
    if _is_windows_dir(norm_target):
        return False

    # Never a protected system directory, or anything inside one.
    for protected in _protected_subtrees():
        norm_protected = os.path.normcase(protected)
        if norm_target == norm_protected or norm_target.startswith(norm_protected + os.sep):
            return False

    # Require real depth below the filesystem anchor.
    try:
        depth = len(p.relative_to(anchor).parts)
    except ValueError:
        return False
    if depth < 2:
        return False

    return True

def hard_delete_directory_contents(path: str) -> tuple[int, int]:
    """
    Permanently deletes all contents of a directory, bypassing the Recycle Bin.
    Extremely fast for Windows caches (Temp, Prefetch, etc).
    Returns (success_count, fail_count).

    Safety: the target is resolved and checked by is_safe_deletion_target()
    first. A refused target returns (0, 1) — counted as a failure so callers
    never log phantom "freed" space for a deletion that did not happen.

    Symlink children are removed as links only (os.remove), never followed;
    a child that is a real directory is removed with shutil.rmtree.
    """
    import shutil
    if not is_safe_deletion_target(path):
        return 0, 1

    target = os.path.realpath(path)

    success_count = 0
    fail_count = 0

    for item in os.listdir(target):
        full_path = os.path.join(target, item)
        try:
            if os.path.isfile(full_path) or os.path.islink(full_path):
                os.remove(full_path)
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
            success_count += 1
        except Exception:
            fail_count += 1

    return success_count, fail_count
