"""Backup: copy a file to .bak before repair."""

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def create_backup(file_path: str, backup_dir: Optional[str] = None) -> str:
    """Copy *file_path* to a timestamped .bak file.

    Returns the backup path.
    Raises FileNotFoundError / OSError on failure.
    """
    src = Path(file_path)
    if not src.is_file():
        raise FileNotFoundError(f'Source not found: {file_path}')

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'{src.stem}_backup_{ts}{src.suffix}.bak'

    if backup_dir:
        dest = Path(backup_dir) / name
        os.makedirs(backup_dir, exist_ok=True)
    else:
        dest = src.parent / name

    shutil.copy2(str(src), str(dest))
    return str(dest)


def verify_backup(original: str, backup: str) -> bool:
    """Return True when SHA-256 of both files match."""
    return _sha256(original) == _sha256(backup)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()
