"""Pure helpers for the Dashboard "Clean Recommended" confirmation.

Kept in core (no Qt import) so the user-visible dialog copy is pinned by
tests; ui/dashboard_tab.py only wraps the result in a QMessageBox.

Why this exists: the Dashboard button is the only destructive action in
the app that ran with no confirmation and no result report. Every other
destructive tab (Workspaces, Development Caches, Windows Storage,
Duplicates, Containers) asks first. This text is the confirmation that
closes that gap.
"""

from core.system_info import format_size


def format_clean_confirmation(items):
    """Return the confirmation text for permanently deleting ``items``.

    ``items`` is a list of {"name": str, "size": int} dicts, as built by
    DashboardTab.clean_recommended from the "Safe" global caches. The
    text names every cache and the total, and states the deletion is
    permanent (bypasses the Recycle Bin/Trash).
    """
    total = sum(i["size"] for i in items)
    noun = "cache" if len(items) == 1 else "caches"
    lines = [
        f"Permanently delete {len(items)} safe global {noun} "
        f"({format_size(total)} total)?",
        "",
        "These files bypass the Recycle Bin/Trash and cannot be restored. "
        "Package managers will redownload what they need.",
        "",
    ]
    for i in items:
        lines.append(f"- {i['name']} ({format_size(i['size'])})")
    return "\n".join(lines)
