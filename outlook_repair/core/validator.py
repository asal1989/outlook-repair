"""Validator: check PST/OST/LST file integrity via header inspection."""

import struct
from pathlib import Path
from typing import List

# PST/OST magic: "!BDN"
_PST_MAGIC = b'\x21\x42\x44\x4E'
# NK2/LST magic
_NK2_MAGIC = b'\x0D\xF0\xAD\xBA'

_PST_VERSIONS = {
    14: 'ANSI (Outlook 97-2002)',
    15: 'ANSI OST (Outlook 97-2002)',
    23: 'Unicode (Outlook 2003-2010)',
    36: 'Unicode (Outlook 2013+)',
}


class ValidationResult:
    def __init__(self):
        self.is_valid: bool = False
        self.file_type: str = 'Unknown'
        self.version: str = 'Unknown'
        self.file_size: int = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def summary(self) -> str:
        if self.errors:
            return f'{self.file_type} — Corrupt ({len(self.errors)} error(s)) — {self.version}'
        return f'{self.file_type} — Valid — {self.version}'


def validate_file(file_path: str) -> ValidationResult:
    result = ValidationResult()
    p = Path(file_path)

    if not p.is_file():
        result.errors.append(f'File not found: {file_path}')
        return result

    result.file_size = p.stat().st_size
    ext = p.suffix.lower()

    if ext in ('.pst', '.ost'):
        _validate_pst_ost(file_path, ext, result)
    elif ext == '.lst':
        _validate_lst(file_path, result)
    else:
        result.warnings.append(f'Unrecognised extension: {ext}')
        result.file_type = 'Unknown'

    result.is_valid = len(result.errors) == 0
    return result


def _validate_pst_ost(path: str, ext: str, r: ValidationResult):
    r.file_type = 'PST' if ext == '.pst' else 'OST'

    if r.file_size < 564:
        r.errors.append(f'File too small ({r.file_size} bytes; minimum 564)')
        return

    try:
        with open(path, 'rb') as f:
            header = f.read(564)

        magic = header[:4]
        if magic != _PST_MAGIC:
            r.errors.append(f'Bad magic bytes: {magic.hex()} (expected {_PST_MAGIC.hex()})')
            return

        if len(header) >= 12:
            ver = struct.unpack_from('<H', header, 10)[0]
            r.version = _PST_VERSIONS.get(ver, f'Unknown version ({ver})')
            if ver not in _PST_VERSIONS:
                r.warnings.append(f'Unrecognised version field: {ver}')

        # Spot-check: can we read the last 4 bytes?
        with open(path, 'rb') as f:
            f.seek(r.file_size - 4)
            tail = f.read(4)
        if len(tail) < 4:
            r.errors.append('File appears truncated (cannot read last 4 bytes)')

    except PermissionError:
        r.errors.append('Permission denied — close Outlook and retry')
    except OSError as e:
        r.errors.append(f'IO error: {e}')


def _validate_lst(path: str, r: ValidationResult):
    r.file_type = 'LST (Autocomplete)'

    if r.file_size == 0:
        r.warnings.append('File is empty')
        r.version = 'Empty'
        return

    try:
        with open(path, 'rb') as f:
            head = f.read(4)
        if head == _NK2_MAGIC:
            r.version = 'NK2 AutoComplete Cache'
        else:
            r.version = 'LST Format'
            if r.file_size < 4:
                r.errors.append(f'File too small ({r.file_size} bytes)')
    except OSError as e:
        r.errors.append(f'IO error: {e}')
