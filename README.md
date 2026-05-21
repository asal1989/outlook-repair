# Outlook File Repair Tool

A Python desktop application for diagnosing, repairing, and recovering data from Microsoft Outlook data files (PST, OST, LST).

## Features

- **Auto-Detection** — Scans your system for PST, OST, and LST files
- **Integrity Validation** — Checks file headers and structure for corruption
- **Repair** — Integrates with Microsoft's `scanpst.exe` (Inbox Repair Tool) on Windows, with a built-in fallback
- **Backup** — Creates a `.bak` copy before any repair operation
- **Email Recovery** — Extracts emails from PST/OST files and saves as EML, CSV, or TXT
- **LST Support** — Detects and repairs Outlook autocomplete list files

## Requirements

- Python 3.8+
- Windows recommended (for `scanpst.exe` integration); core features work cross-platform
- Optional: `pypff` for advanced PST/OST reading during recovery

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

### GUI Mode

```bash
python -m outlook_repair
```

Or after installation:

```bash
outlook-repair
```

### Workflow

1. **Scanner tab** — Click *Scan System* to find all PST/OST/LST files, or use *Add File...* / *Add Folder...*
2. Select a file and click *Use Selected* (or double-click) to send it to the Repair tab
3. **Repair tab** — Click *Validate* to check integrity, then *Repair* to fix issues
4. **Recovery tab** — Choose output format (EML / CSV / TXT) and click *Start Recovery* to extract emails
5. **Log tab** — Full activity log; save it with *Save Log...*

## Supported Formats

| Format | Description | Validate | Repair | Extract Emails |
|--------|-------------|----------|--------|----------------|
| `.pst` | Personal Storage Table | ✓ | ✓ | ✓ |
| `.ost` | Offline Storage Table | ✓ | ✓ | ✓ |
| `.lst` | Outlook Autocomplete List | ✓ | ✓ | — |

## Optional Dependency

Install `pypff` for best email recovery results:

```bash
pip install pypff
```

Without it, the tool falls back to raw byte scanning which recovers partial data.

## License

MIT License
