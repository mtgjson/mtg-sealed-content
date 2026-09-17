"""Publish complete text files without exposing partially written contents."""
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import tempfile


def _default_file_mode():
    """Return the mode a normal ``open(..., \"w\")`` would use."""
    current_umask = os.umask(0)
    try:
        return 0o666 & ~current_umask
    finally:
        os.umask(current_umask)


@contextmanager
def atomic_write(path, *, encoding="utf-8"):
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding=encoding, dir=destination.parent,
            prefix=f".{destination.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            if destination.exists():
                temporary.chmod(stat.S_IMODE(destination.stat().st_mode))
            else:
                temporary.chmod(_default_file_mode())
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
