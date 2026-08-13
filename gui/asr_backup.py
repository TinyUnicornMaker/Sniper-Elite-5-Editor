"""Stock snapshots next to game archives.

A ``.bak`` is only created from a file that already looks healthy.
Restore refuses a damaged backup, copies via a temp file, then checks
that the restored bytes match the backup.

The old ``if not exists: copy2(current, bak)`` path is unsafe: the first
editor write can snapshot an already-modified ``common.asr``. Restore then
succeeds and the game still crashes.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile

from gui.zbb_util import validate_zbb

_CHUNK = 8 * 1024 * 1024


def bak_path(path: str) -> str:
    return path if path.endswith(".bak") else path + ".bak"


def file_digest(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def looks_healthy(path: str) -> str | None:
    """Return an error string if *path* should not be used as a snapshot."""
    if not path or not os.path.isfile(path):
        return "file not found"
    size = os.path.getsize(path)
    if size < 16:
        return "file is too small"
    with open(path, "rb") as fh:
        magic = fh.read(8)
    name = os.path.basename(path).lower()
    is_base_asr = name.startswith("common.asr") and ".asrpatch" not in name
    if is_base_asr or magic == b"AsuraZbb":
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
            return validate_zbb(raw)
        except Exception as exc:
            return str(exc)
    if magic not in (b"AsuraZlb", b"AsuraZbb", b"Asura   "):
        return f"unrecognised header {magic!r}"
    return None


def ensure_backup(path: str) -> tuple[bool, str]:
    """Create ``path.bak`` from a healthy *path*. Never snapshot a broken file.

    If a backup already exists but fails the health check, and *path* is
    healthy, the backup is replaced. A healthy backup is left untouched
    so later edits do not overwrite the snapshot.
    """
    if not path or path.endswith(".bak"):
        return False, "refusing to snapshot a .bak path"
    err = looks_healthy(path)
    if err:
        return False, f"not snapshotting a damaged file ({err})"
    bak = bak_path(path)
    if os.path.isfile(bak):
        bak_err = looks_healthy(bak)
        if bak_err is None:
            return True, f"backup already exists ({os.path.basename(bak)})"
        # Poisoned leftover from an earlier crash-causing write.
        try:
            os.remove(bak)
        except OSError as exc:
            return False, f"could not replace damaged backup: {exc}"
    try:
        shutil.copy2(path, bak)
    except OSError as exc:
        return False, f"could not create backup: {exc}"
    bak_err = looks_healthy(bak)
    if bak_err:
        try:
            os.remove(bak)
        except OSError:
            pass
        return False, f"backup copy failed health check ({bak_err})"
    return True, f"created {os.path.basename(bak)}"


def restore_backup(path: str) -> tuple[bool, str]:
    """Copy ``path.bak`` over *path* after validating both the backup and the copy."""
    if not path:
        return False, "no path"
    dest = path[:-4] if path.endswith(".bak") else path
    bak = bak_path(dest)
    if not os.path.isfile(bak):
        return False, f"{os.path.basename(bak)} was not found"
    bak_err = looks_healthy(bak)
    if bak_err:
        return False, (
            f"{os.path.basename(bak)} failed its health check ({bak_err}). "
            "Do not restore it — verify game files in Steam instead."
        )
    if os.path.isfile(dest) and file_digest(bak) == file_digest(dest):
        return True, f"{os.path.basename(dest)} already matches its backup"
    directory = os.path.dirname(dest) or "."
    fd, tmp = tempfile.mkstemp(
        prefix=os.path.basename(dest) + ".", suffix=".restoring", dir=directory
    )
    os.close(fd)
    try:
        shutil.copy2(bak, tmp)
        if file_digest(tmp) != file_digest(bak):
            return False, "restore copy did not match the backup; left the live file alone"
        os.replace(tmp, dest)
        tmp = ""
    except OSError as exc:
        return False, f"restore failed: {exc}"
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    dest_err = looks_healthy(dest)
    if dest_err:
        return False, (
            f"restored file failed its health check ({dest_err}). "
            "Verify game files in Steam."
        )
    return True, f"restored {os.path.basename(dest)} from {os.path.basename(bak)}"


def clear_backup(path: str) -> tuple[bool, str]:
    bak = bak_path(path)
    if not os.path.isfile(bak):
        return True, "no backup to remove"
    try:
        os.remove(bak)
    except OSError as exc:
        return False, str(exc)
    return True, f"removed {os.path.basename(bak)}"
