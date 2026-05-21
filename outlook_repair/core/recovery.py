"""Recovery: extract emails from PST/OST files as EML, CSV, or TXT."""

import csv
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple


class EmailRecord:
    def __init__(self):
        self.subject: str = ''
        self.sender: str = ''
        self.recipients: str = ''
        self.date: str = ''
        self.body: str = ''
        self.message_id: str = ''

    def to_eml(self) -> str:
        lines = []
        if self.sender:
            lines.append(f'From: {self.sender}')
        if self.recipients:
            lines.append(f'To: {self.recipients}')
        if self.subject:
            lines.append(f'Subject: {self.subject}')
        if self.date:
            lines.append(f'Date: {self.date}')
        if self.message_id:
            lines.append(f'Message-ID: {self.message_id}')
        lines += ['MIME-Version: 1.0', 'Content-Type: text/plain; charset=utf-8', '']
        lines.append(self.body or '(No body)')
        return '\n'.join(lines)

    def to_dict(self) -> Dict:
        return {
            'Subject': self.subject,
            'From': self.sender,
            'To': self.recipients,
            'Date': self.date,
            'Message-ID': self.message_id,
            'Body': self.body[:500],
        }


def recover_emails(
    file_path: str,
    output_dir: str,
    output_format: str = 'eml',
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict:
    result: Dict = {'recovered': 0, 'failed': 0, 'output_dir': output_dir, 'errors': []}

    def log(msg: str):
        if progress_callback:
            progress_callback(msg)

    os.makedirs(output_dir, exist_ok=True)

    ext = Path(file_path).suffix.lower()
    if ext not in ('.pst', '.ost'):
        result['errors'].append(f'Email recovery is not supported for {ext} files')
        return result

    pypff_ok, pypff_count = _pypff_recovery(file_path, output_dir, output_format, result, log)
    if not pypff_ok or pypff_count == 0:
        if pypff_ok and pypff_count == 0:
            log('pypff found 0 messages — trying raw byte scan as fallback')
        else:
            log('pypff not available — falling back to raw byte scan (partial data only)')
        _raw_recovery(file_path, output_dir, output_format, result, log)

    return result


# ---------------------------------------------------------------------------
# pypff path
# ---------------------------------------------------------------------------

def _pypff_recovery(
    file_path: str, output_dir: str, fmt: str,
    result: Dict, log: Callable,
) -> Tuple[bool, int]:
    """Return (attempted, messages_found)."""
    try:
        import pypff  # type: ignore
    except ImportError:
        return False, 0

    try:
        log('Opening file with pypff...')
        pff = pypff.file()
        pff.open(file_path)
        emails: List[EmailRecord] = []
        _walk_pypff(pff.get_root_folder(), emails, log)
        pff.close()
        count = len(emails)
        log(f'pypff found {count} message(s)')
        if count > 0:
            _save(emails, output_dir, fmt, result, log)
        return True, count
    except Exception as e:
        log(f'pypff error: {e}')
        return False, 0


def _walk_pypff(folder, emails: List[EmailRecord], log: Callable):
    try:
        for i in range(folder.number_of_sub_messages):
            try:
                msg = folder.get_sub_message(i)
                rec = EmailRecord()
                for attr in ('subject', 'sender_name', 'plain_text_body'):
                    try:
                        val = getattr(msg, attr, '') or ''
                        if isinstance(val, bytes):
                            val = val.decode('utf-8', errors='replace')
                        if attr == 'subject':
                            rec.subject = val
                        elif attr == 'sender_name':
                            rec.sender = val
                        else:
                            rec.body = val
                    except Exception:
                        pass
                emails.append(rec)
            except Exception:
                pass
        for i in range(folder.number_of_sub_folders):
            try:
                _walk_pypff(folder.get_sub_folder(i), emails, log)
            except Exception:
                pass
    except Exception as e:
        log(f'Folder walk error: {e}')


# ---------------------------------------------------------------------------
# Raw byte scan fallback
# ---------------------------------------------------------------------------

def _raw_recovery(
    file_path: str, output_dir: str, fmt: str,
    result: Dict, log: Callable,
):
    log('Scanning raw bytes for email headers...')
    emails: List[EmailRecord] = []
    # Deduplicate by (subject, sender) to avoid re-adding emails from the
    # overlap region that is carried over between chunks.
    seen: Set[Tuple[str, str]] = set()
    chunk_size = 1024 * 1024
    # Overlap must be >= max lookbehind (200) + len('Subject: ') so a header
    # spanning a chunk boundary is not missed entirely.
    overlap = 4096

    try:
        fsize = os.path.getsize(file_path)
        log(f'File size: {fsize:,} bytes')
        tail = b''
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                buf = tail + data
                pos = 0
                while True:
                    idx = buf.find(b'Subject: ', pos)
                    if idx == -1:
                        break
                    fragment = buf[max(0, idx - 200): idx + 2000]
                    rec = _parse_fragment(fragment)
                    if rec:
                        key = (rec.subject, rec.sender)
                        if key not in seen:
                            seen.add(key)
                            emails.append(rec)
                            log(f'Found: {rec.subject[:60]}')
                    pos = idx + 1
                    if len(emails) >= 2000:
                        break
                if len(emails) >= 2000:
                    break
                # Keep an overlap tail so headers spanning chunk boundaries are caught
                tail = buf[-overlap:]
    except OSError as e:
        result['errors'].append(f'Read error: {e}')
        return

    log(f'Raw scan complete — {len(emails)} unique fragment(s) found')
    _save(emails, output_dir, fmt, result, log)


def _parse_fragment(data: bytes) -> Optional[EmailRecord]:
    try:
        text = data.decode('utf-8', errors='replace')
        rec = EmailRecord()
        for line in text.splitlines():
            low = line.lower()
            if low.startswith('subject:'):
                rec.subject = line[8:].strip()
            elif low.startswith('from:'):
                rec.sender = line[5:].strip()
            elif low.startswith('to:'):
                rec.recipients = line[3:].strip()
            elif low.startswith('date:'):
                rec.date = line[5:].strip()
        return rec if rec.subject else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def _save(
    emails: List[EmailRecord], output_dir: str, fmt: str,
    result: Dict, log: Callable,
):
    if fmt == 'csv':
        _save_csv(emails, output_dir, result, log)
    elif fmt == 'txt':
        _save_txt(emails, output_dir, result, log)
    else:
        _save_eml(emails, output_dir, result, log)


def _save_eml(emails: List[EmailRecord], output_dir: str, result: Dict, log: Callable):
    for i, rec in enumerate(emails):
        safe = ''.join(
            c for c in (rec.subject or f'email_{i+1}')[:50]
            if c.isalnum() or c in ' ._-'
        ).strip() or f'email_{i+1}'
        path = os.path.join(output_dir, f'{i+1:04d}_{safe}.eml')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(rec.to_eml())
            result['recovered'] += 1
        except OSError as e:
            result['failed'] += 1
            result['errors'].append(f'Cannot write {path}: {e}')
    log(f'Saved {result["recovered"]} EML file(s) to {output_dir}')


def _save_csv(emails: List[EmailRecord], output_dir: str, result: Dict, log: Callable):
    path = os.path.join(output_dir, 'recovered_emails.csv')
    try:
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(
                f, fieldnames=['Subject', 'From', 'To', 'Date', 'Message-ID', 'Body'])
            writer.writeheader()
            for rec in emails:
                writer.writerow(rec.to_dict())
                result['recovered'] += 1
        log(f'Saved {result["recovered"]} row(s) to {path}')
    except OSError as e:
        result['errors'].append(f'CSV write error: {e}')


def _save_txt(emails: List[EmailRecord], output_dir: str, result: Dict, log: Callable):
    path = os.path.join(output_dir, 'recovered_emails.txt')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            for i, rec in enumerate(emails):
                f.write(f'{"="*60}\nEmail #{i+1}\n{"="*60}\n')
                f.write(f'Subject: {rec.subject}\nFrom: {rec.sender}\n'
                        f'To: {rec.recipients}\nDate: {rec.date}\n\n'
                        f'{rec.body}\n\n')
                result['recovered'] += 1
        log(f'Saved {result["recovered"]} email(s) to {path}')
    except OSError as e:
        result['errors'].append(f'TXT write error: {e}')
