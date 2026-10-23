"""Byte-identical duplicate file finder, backing the future Duplicates tab.

Grouping is two-stage: files are first bucketed by size (cheap — stat only),
then only size-buckets with more than one member are hashed with SHA-256.
Groups come back sorted by reclaimable bytes, largest first.

Safety properties (this app deletes files, so the scanner must be conservative):
- Symlinks are NEVER followed: symlinked directories are not descended into
  and symlinked files are not hashed or grouped.
- Hardlinks (same device + inode) are collapsed: the same bytes on disk are
  never presented as two "copies".
- Non-absolute, missing, or non-directory scan roots are refused, consistent
  with core.trash.is_safe_deletion_target() which refuses relative paths.
- Unreadable files and directories are collected in ``errors``, never raised.

Deletion is deliberately NOT in this module. The UI trashes user-chosen
copies through core.trash.safe_delete (OS Recycle Bin/Trash) via
``trash_duplicates`` below — never os.remove, never a new raw delete.
"""

import hashlib
import os

from core import trash

# Hash I/O granularity: 1 MiB chunks keep memory flat on multi-GB files.
CHUNK_SIZE = 1024 * 1024

# Files smaller than this are skipped. Default 1: empty files hash
# identically but grouping thousands of 0-byte files is noise, not cleanup.
MIN_SIZE_DEFAULT = 1

# Progress callback granularity during the walk phase.
_PROGRESS_EVERY_N_FILES = 256


def _sha256_of(path: str) -> str:
    """SHA-256 hex digest of a file, streamed so large files stay flat."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_regular_files(roots, errors, on_progress):
    """Yield (size, path) for every regular file under roots.

    Symlinks are never followed; hardlinks collapse to one entry per inode.
    Problems go into ``errors``; nothing raises.
    """
    seen_inodes = set()
    files_seen = 0

    def visit(dir_path):
        nonlocal files_seen
        try:
            with os.scandir(dir_path) as it:
                entries = list(it)
        except OSError as e:
            errors.append(f"unreadable directory: {dir_path} ({e})")
            return
        for entry in entries:
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    yield from visit(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    st = entry.stat(follow_symlinks=False)
                    inode = (st.st_dev, st.st_ino)
                    if inode in seen_inodes:
                        continue  # hardlink to an already-seen file
                    seen_inodes.add(inode)
                    files_seen += 1
                    if on_progress and files_seen % _PROGRESS_EVERY_N_FILES == 0:
                        on_progress(files_seen)
                    yield st.st_size, os.path.realpath(entry.path)
            except OSError as e:
                errors.append(f"unreadable: {entry.path} ({e})")

    for root in roots:
        if not isinstance(root, str) or not os.path.isabs(root):
            errors.append(f"refused non-absolute root: {root!r}")
            continue
        real_root = os.path.realpath(root)
        if not os.path.isdir(real_root):
            errors.append(f"refused missing root: {root!r}")
            continue
        yield from visit(real_root)


def find_duplicates(roots, min_size=MIN_SIZE_DEFAULT, on_progress=None):
    """Find groups of byte-identical files under ``roots``.

    Args:
        roots: absolute directory paths to scan.
        min_size: files smaller than this many bytes are ignored.
        on_progress: optional callable invoked as ``on_progress(files_seen)``
            roughly every 256 files during the walk phase.

    Returns:
        (groups, errors) where each group is
        ``{"size": int, "sha256": str, "paths": [str, ...]}`` and groups are
        sorted by reclaimable bytes (size * (copies - 1)) descending.
        ``errors`` lists refused roots and unreadable paths; the scan
        never aborts on a single bad path.
    """
    errors = []
    by_size = {}
    for size, path in _iter_regular_files(roots, errors, on_progress):
        if size < min_size:
            continue
        by_size.setdefault(size, []).append(path)

    groups = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash = {}
        for path in paths:
            try:
                digest = _sha256_of(path)
            except OSError as e:
                errors.append(f"unreadable: {path} ({e})")
                continue
            by_hash.setdefault(digest, []).append(path)
        for digest, dup_paths in by_hash.items():
            if len(dup_paths) < 2:
                continue
            groups.append({"size": size, "sha256": digest,
                           "paths": sorted(dup_paths)})

    groups.sort(key=lambda g: g["size"] * (len(g["paths"]) - 1),
                reverse=True)
    return groups, errors


def group_reclaimable_bytes(group) -> int:
    """Bytes freed by trashing every copy in ``group`` except one."""
    return group["size"] * (len(group["paths"]) - 1)


def trash_duplicates(paths):
    """Move ``paths`` to the OS Recycle Bin/Trash via the safe trash path.

    This is the ONLY sanctioned way to remove duplicates: each path goes
    through core.trash.safe_delete, so nothing is ever permanently deleted
    and a misclick is recoverable. Returns (trashed_count, failed_count).
    """
    trashed = 0
    failed = 0
    for path in paths:
        try:
            if trash.safe_delete(path):
                trashed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return trashed, failed
