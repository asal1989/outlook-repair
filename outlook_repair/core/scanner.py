"""Scanner: locate PST/OST/LST files on the filesystem."""

import os
import platform
import threading
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Set

# Immutable so callers cannot accidentally corrupt the module default
OUTLOOK_EXTENSIONS: FrozenSet[str] = frozenset({'.pst', '.ost', '.lst'})

_FILE_TYPE_NAMES = {
    '.pst': 'Personal Storage Table',
    '.ost': 'Offline Storage Table',
    '.lst': 'Outlook List File',
}


def get_default_scan_paths() -> List[str]:
    if platform.system() == 'Windows':
        return [
            os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Outlook'),
            os.path.expandvars(r'%APPDATA%\Microsoft\Outlook'),
            os.path.expandvars(r'%USERPROFILE%\Documents'),
            os.path.expandvars(r'%USERPROFILE%'),
        ]
    return [os.path.expanduser('~')]


def scan_directory(
    directory: str,
    extensions: Optional[Set[str]] = None,
    callback: Optional[Callable[[Dict], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> List[Dict]:
    """Recursively scan *directory* for Outlook data files.

    Each found file is reported as a dict with keys:
        path, name, size, size_str, extension, type
    """
    if extensions is None:
        extensions = OUTLOOK_EXTENSIONS

    found: List[Dict] = []
    root = Path(directory)

    if not root.is_dir():
        return found

    try:
        for item in root.rglob('*'):
            if stop_event and stop_event.is_set():
                break
            if item.is_file() and item.suffix.lower() in extensions:
                try:
                    info = _build_info(item)
                    found.append(info)
                    if callback:
                        callback(info)
                except OSError:
                    pass
    except OSError:
        pass

    return found


def _build_info(path: Path) -> Dict:
    size = path.stat().st_size
    ext = path.suffix.lower()
    return {
        'path': str(path),
        'name': path.name,
        'size': size,
        'size_str': _fmt_size(size),
        'extension': ext,
        'type': _FILE_TYPE_NAMES.get(ext, 'Unknown'),
    }


def _fmt_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} PB'
