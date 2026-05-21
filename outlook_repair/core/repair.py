"""Repair: run scanpst.exe or built-in structural repair on PST/OST/LST files."""

import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

_SCANPST_CANDIDATES = [
    r'C:\Program Files\Microsoft Office\root\Office16\SCANPST.EXE',
    r'C:\Program Files (x86)\Microsoft Office\root\Office16\SCANPST.EXE',
    r'C:\Program Files\Microsoft Office\Office16\SCANPST.EXE',
    r'C:\Program Files (x86)\Microsoft Office\Office16\SCANPST.EXE',
    r'C:\Program Files\Microsoft Office\Office15\SCANPST.EXE',
    r'C:\Program Files (x86)\Microsoft Office\Office15\SCANPST.EXE',
    r'C:\Program Files\Microsoft Office\Office14\SCANPST.EXE',
    r'C:\Program Files (x86)\Microsoft Office\Office14\SCANPST.EXE',
    r'C:\Program Files\Microsoft Office\Office12\SCANPST.EXE',
    r'C:\Program Files (x86)\Microsoft Office\Office12\SCANPST.EXE',
]


def find_scanpst() -> Optional[str]:
    if platform.system() != 'Windows':
        return None
    for p in _SCANPST_CANDIDATES:
        if os.path.isfile(p):
            return p
    return _find_scanpst_via_registry()


def _find_scanpst_via_registry() -> Optional[str]:
    try:
        import winreg
        keys = [
            r'SOFTWARE\Microsoft\Office\16.0\Outlook\InstallRoot',
            r'SOFTWARE\Microsoft\Office\15.0\Outlook\InstallRoot',
            r'SOFTWARE\Microsoft\Office\14.0\Outlook\InstallRoot',
            r'SOFTWARE\WOW6432Node\Microsoft\Office\16.0\Outlook\InstallRoot',
        ]
        for key_path in keys:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    install_dir, _ = winreg.QueryValueEx(key, 'Path')
                candidate = os.path.join(install_dir, 'SCANPST.EXE')
                if os.path.isfile(candidate):
                    return candidate
            except OSError:
                continue
    except ImportError:
        pass
    return None


class RepairResult:
    def __init__(self):
        self.success: bool = False
        self.method: str = 'none'
        self.output: List[str] = []
        self.errors: List[str] = []
        self.backup_path: Optional[str] = None


def repair_file(
    file_path: str,
    backup_path: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> RepairResult:
    result = RepairResult()
    result.backup_path = backup_path

    def log(msg: str):
        result.output.append(msg)
        if progress_callback:
            progress_callback(msg)

    p = Path(file_path)
    if not p.is_file():
        result.errors.append(f'File not found: {file_path}')
        return result

    ext = p.suffix.lower()

    if ext in ('.pst', '.ost'):
        scanpst = find_scanpst()
        if scanpst:
            log(f'Found scanpst.exe: {scanpst}')
            _run_scanpst(file_path, scanpst, result, log, stop_event)
        else:
            log('scanpst.exe not found — running built-in repair')
            _builtin_pst_repair(file_path, result, log, stop_event)
    elif ext == '.lst':
        _repair_lst(file_path, result, log)
    else:
        result.errors.append(f'Unsupported file type: {ext}')

    return result


def _run_scanpst(
    file_path: str,
    scanpst: str,
    result: RepairResult,
    log: Callable,
    stop_event: Optional[threading.Event],
):
    result.method = 'scanpst.exe'
    log(f'Launching scanpst.exe on: {file_path}')
    log('NOTE: scanpst.exe may open a dialog requiring manual interaction.')
    try:
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        proc = subprocess.Popen(
            [scanpst, file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=flags,
        )
        while proc.poll() is None:
            if stop_event and stop_event.is_set():
                proc.terminate()
                result.errors.append('Repair cancelled')
                return
            time.sleep(0.5)

        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            result.success = True
            log('scanpst.exe completed successfully.')
        else:
            result.errors.append(f'scanpst.exe exited with code {proc.returncode}')
        if stdout:
            log(stdout.decode('utf-8', errors='replace').strip())
        if stderr:
            log(stderr.decode('utf-8', errors='replace').strip())

    except OSError as e:
        result.errors.append(f'Failed to launch scanpst.exe: {e}')


def _builtin_pst_repair(
    file_path: str,
    result: RepairResult,
    log: Callable,
    stop_event: Optional[threading.Event],
):
    """Minimal built-in repair: restore magic bytes if corrupted."""
    result.method = 'built-in'
    log('Running built-in PST/OST repair...')
    _PST_MAGIC = b'\x21\x42\x44\x4E'
    try:
        with open(file_path, 'r+b') as f:
            magic = f.read(4)
            if magic != _PST_MAGIC:
                log(f'Bad magic ({magic.hex()}) — restoring...')
                f.seek(0)
                f.write(_PST_MAGIC)
                log('Magic bytes restored.')
            else:
                log('Magic bytes are intact.')
        log('Built-in repair complete. For deep repair use scanpst.exe on Windows.')
        result.success = True
    except PermissionError:
        result.errors.append('Permission denied — close Outlook and retry')
    except OSError as e:
        result.errors.append(f'IO error: {e}')


def _repair_lst(file_path: str, result: RepairResult, log: Callable):
    result.method = 'lst-repair'
    log(f'Repairing LST file: {file_path}')
    _NK2_MAGIC = b'\x0D\xF0\xAD\xBA'
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            with open(file_path, 'wb') as f:
                f.write(_NK2_MAGIC + b'\x00' * 8)
            log('Empty LST recreated with valid header.')
            result.success = True
            return
        with open(file_path, 'rb') as f:
            head = f.read(4)
        if head == _NK2_MAGIC:
            log('LST header is valid — no repair needed.')
            result.success = True
        else:
            result.errors.append(
                'LST header invalid. Delete the file and let Outlook recreate it.'
            )
    except OSError as e:
        result.errors.append(f'IO error: {e}')
