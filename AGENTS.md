# AGENTS.md

## Quick start

```bash
pip install -r requirements.txt
generate_report.bat            # or:
cd handler && python main_menu.py
```

## CWD must be `handler/`

All Python scripts use relative paths like `../system_check/logs`. Running from repo root breaks every path. The `.bat` launcher handles this automatically.

## Menu

| Key | Action |
|-----|--------|
| 1 | rsync download XML from remote servers |
| 2 | Parse XML → generate Word reports → `check_report/` |
| 3 | Delete (y/N) `system_check/logs/` and `oracle_check/logs/` |
| 0 | Exit |

Report order: server first, then database. On failure, print error and pause — do NOT continue.

## Must-configure placeholders

- `handler/remote_downloader.py`: `[yourpassword]`, `[user]@[server_ip]` (lines 21-22)
- `scripts/system_check.sh`, `scripts/oracle_check.sh`: `[user]@[server_ip]` (ssh/scp targets)

## Remote scripts (run on target servers, not locally)

- Require **root**; support Anolis / CentOS / Ubuntu / RedHat / Oracle Linux only
- Require `/etc/assetname` formatted as `project name-system name-192.168.0.1`
- `ora_check_xml.sh` auto-detects Oracle user (`oracle` or `oracle12c`)
- Upload direction (SSH): port **8859**; Download direction (rsync): port **8858**

## Report quirks

- Filename: `YYYY-MM<projectname><type>巡检报告.doc` — `.doc` extension despite docxtpl + `.docx` templates
- Default inspector name when blank: `巡检人`
- Matplotlib charts (database reports) require **SimHei** font installed on the generating machine

## XML data layout

```
system_check/logs/<project>/<hosthash>/system_check_<timestamp>.xml
oracle_check/logs/<project>/<hosthash>/oracle_check_<timestamp>.xml
```

`folder_handler.py` sorts files by numeric suffix to find the latest per host.

## No test / lint infrastructure

No tests, no CI, no lint config, no type checking. Only runtime errors will surface problems.

## File map

| File | Role |
|---|---|
| `handler/main_menu.py` | Entry point — interactive menu loop |
| `handler/scheduler.py` | `generate_server_report()` / `generate_database_report()` |
| `handler/remote_downloader.py` | rsync download with Cygwin path conversion |
| `handler/local_cleaner.py` | Delete and recreate log dirs |
| `handler/folder_handler.py` | Walk `logs/<project>/<hosthash>/`, find latest XML |
| `handler/xml_handler.py` | XPath parser (lxml preferred, elementtree fallback) |
| `handler/server_word_handler.py` | 21 threshold checks + Chinese advice + Word generation |
| `handler/database_word_handler.py` | Disk/CPU/memory charts (matplotlib) + Word generation |
| `handler/server_template.docx` | Word template for server reports |
| `handler/database_template.docx` | Word template for database reports |
| `scripts/*.sh` | Deploy to remote servers to collect XML data |
| `cwRsync/rsync.exe` | Bundled rsync for Windows |
