"""Dashboard headline-number arithmetic, kept Qt-free so it is testable.

"Total Recoverable Space" on the Dashboard must only count space that
deleting a cache actually returns:

- global caches (deletable from the Development Caches tab) — counted;
- Windows storage items (deletable from the Windows Storage tab,
  including the Recycle Bin) — counted;
- WSL vhdx files — NOT counted. Compacting a vhdx returns only its slack
  space, which is unknown until compaction runs; counting the whole
  vhdx size as "recoverable" overstates the headline number by the
  full disk size. The vhdx sizes are still reported separately in
  ``wsl_distros`` for the Docker / WSL card and breakdown.
- ``docker_df`` entries — NOT counted. They carry unparsed size strings
  (e.g. "5.2GB"), not byte counts, so there is nothing safe to add.
"""


def total_recoverable_bytes(stats: dict) -> int:
    """Bytes the Dashboard may headline as recoverable.

    ``stats`` is the aggregator dict with ``global_caches``,
    ``windows_storage``, ``wsl_distros`` and ``docker_df`` keys.
    Missing keys and missing ``size_bytes`` values count as 0.
    """
    total = 0
    for cache in stats.get("global_caches") or []:
        total += cache.get("size_bytes", 0) or 0
    for item in stats.get("windows_storage") or []:
        total += item.get("size_bytes", 0) or 0
    return total
