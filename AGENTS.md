# AGENTS.md

## Quick start

```bash
# Install dependencies (Windows, from repo root)
pip install docxtpl matplotlib lxml
# or
pip install -r requirements.txt

# Run the tool
generate_report.bat
# or directly:
cd handler && python main_menu.py
```

## Architecture

Single `handler/` directory contains all Python code. No separate subsystem directories for code — only `system_check/logs/` and `ora_check/logs/` hold downloaded XML data.

Entry point chain: `generate_report.bat` → `cd handler` → `python main_menu.py`

The menu (1=download, 2=generate reports, 3=delete local XML, 0=exit) drives everything. Report generation calls `scheduler.py` which delegates to `server_word_handler.py` and `database_word_handler.py`.

## Key facts

- **CWD must be `handler/`** — all Python scripts use relative paths like `../system_check/logs`. Running from repo root breaks path resolution.
- **Reports saved as `.doc`** (not `.docx`) despite using docx templates via docxtpl.
- **Charts require SimHei font** — `database_word_handler.py` sets `plt.rcParams['font.sans-serif'] = ['SimHei']` for Chinese text in matplotlib charts.
- **rsync credentials hardcoded** in `remote_downloader.py` — host, port, password, module names (`systemxml`, `dbxml`).
- **UTF-8 stdout** explicitly set in `main_menu.py:13` — `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`.
- **lxml preferred** over stdlib ElementTree (see `xml_handler.py:12-17` fallback).
- **XML naming convention**: files are `system_check_<timestamp>.xml` and `ora_check_<timestamp>.xml`. `folder_handler.py` sorts by numeric suffix to find the latest.
- **Remote servers must have `/etc/assetname`** with format `school name-system name-192.168.0.1` — shell scripts will exit if missing.
- **Shell scripts require root** and only support Anolis/CentOS/Ubuntu/RedHat/Oracle Linux.
- **Upload uses SSH on port 8859**, download uses rsync on port 8858 — different ports for different directions.

## Workflow

1. Menu option 1: Downloads XML via rsync (cwRsync on Windows, Cygwin path conversion)
2. Menu option 2: Parses XML → generates Word reports → saves to `check_report/`
3. Menu option 3: Deletes `system_check/logs/` and `ora_check/logs/` (requires y/N confirmation)

Report generation order: server first, then database. If any report fails, output error and pause — do NOT continue.

## File map

| File | Purpose |
|---|---|
| `handler/main_menu.py` | Interactive menu entry point |
| `handler/scheduler.py` | `generate_server_report()` / `generate_database_report()` |
| `handler/remote_downloader.py` | rsync download, Cygwin path conversion |
| `handler/local_cleaner.py` | Delete and recreate log directories |
| `handler/folder_handler.py` | Walk `logs/<school>/<hosthash>/`, find latest XML per host |
| `handler/xml_handler.py` | XPath parser for section/member/node elements |
| `handler/server_word_handler.py` | 21 threshold checks + Chinese advice + Word generation |
| `handler/database_word_handler.py` | Disk/CPU/memory analysis + matplotlib charts + Word generation |
| `handler/server_template.docx` | Word template for server reports |
| `handler/database_template.docx` | Word template for database reports |
| `cwRsync/rsync.exe` | Bundled rsync binary for Windows |
| `scripts/*.sh` | Remote XML collection scripts (run on target servers) |
| `scripts/*.sh.x` | Encrypted/compiled versions of the shell scripts |

## Conventions

- All Python files: UTF-8 encoding (`# -*- coding: utf-8 -*-`)
- Chinese language for all UI messages, comments, and report content
- Default inspector name: '售后运维部' when user leaves input blank
- Output reports named: `YYYY-MM<schoolname><type>巡检报告.doc`
- Destructive operations (delete files) require explicit user confirmation (y/N)
