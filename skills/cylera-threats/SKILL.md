---
name: cylera-threats
description: Export Cylera threats to CSV with optional filters for severity, status, and detection window. Use when the user wants a snapshot of active threats, e.g. "all HIGH open threats" or "threats detected in the last 7 days".
argument-hint: [severity] [status] [last N days | last week | Nd]
allowed-tools: Bash, Write, AskUserQuestion
---

Query Cylera for detected threats and export the results to a CSV file. Supports optional filters for severity, status, and detection window.

## Arguments

`$ARGUMENTS` may contain any combination of:
- A severity level: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- A status: `OPEN`, `IN_PROGRESS`, `RESOLVED`, `SUPPRESSED`
- An optional detection window: `last N days`, `last week`, `Nd` (e.g. `30d`)

Examples:
- (empty) — all threats
- `HIGH` — all HIGH threats regardless of status
- `CRITICAL OPEN` — open CRITICAL threats
- `HIGH last 30 days` — HIGH threats detected in the last 30 days
- `OPEN 7d` — open threats detected in the last 7 days

If no arguments are provided, ask the user what filters they want to apply.

## Steps

### 1. Detect credentials and parse arguments (run in parallel if arguments are known)

If `$ARGUMENTS` is provided, run both sub-steps simultaneously. Otherwise, run step 1a first, then ask.

**1a) Detect credentials — single Bash call:**
```
(which doppler 2>/dev/null && echo "doppler_found") || \
(which op 2>/dev/null && [ -n "$OP_ENVIRONMENT_ID" ] && echo "op_found") || \
([ -f .env ] && echo "dotenv_found") || \
echo "none"
```
- `doppler_found` → use `doppler run --` as the command prefix
- `op_found` → use `op run --environment "$OP_ENVIRONMENT_ID" --` as the command prefix
- `dotenv_found` → use no prefix
- `none` → offer to run `cylera init`. If the user agrees, run it and use no prefix. If they decline, stop.

**1b) Parse arguments:**

Extract filters from `$ARGUMENTS`:
- Severity: one of `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` (case-insensitive)
- Status: one of `OPEN`, `IN_PROGRESS`, `RESOLVED`, `SUPPRESSED` (case-insensitive)
- Detection window: `last week` → 7 days; `last N days` or `Nd` → N days; absent → no filter
- Unknown tokens: ignore

### 2. Run the fetch-and-export script

Substitute `SEVERITY`, `STATUS`, `DAYS`, and `PREFIX` before running. Use empty string for unused filters, integer for days (0 = no filter).

```bash
PREFIX="<prefix>" python3 - << 'PYEOF'
import subprocess, json, csv, sys, datetime, os
from pathlib import Path
from collections import Counter

severity = "<severity>"   # e.g. "HIGH" or ""
status = "<status>"       # e.g. "OPEN" or ""
days = <days>             # 0 means no filter
prefix = os.environ.get("PREFIX", "").split() if os.environ.get("PREFIX") else []

date = datetime.date.today().isoformat()
cutoff_ts = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp() if days else None

parts = []
if severity:
    parts.append(severity.lower())
if status:
    parts.append(status.lower())
if days:
    parts.append(f"last{days}days")
slug = "-".join(parts) if parts else "all"
filepath = Path.cwd() / f"cylera-threats-{slug}-{date}.csv"

columns = ["mac_address", "device_hostname", "device_ip", "name",
           "severity", "status", "detected_at"]

cmd = prefix + ["cylera", "threats", "--page-size", "100"]
if severity:
    cmd += ["--severity", severity.upper()]
if status:
    cmd += ["--status", status.upper()]

rows = []
page = 0

while True:
    result = subprocess.run(
        cmd + ["--page", str(page)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(json.dumps({"error": result.stderr}))
        sys.exit(1)
    data = json.loads(result.stdout)
    threats = data.get("threats", [])
    for t in threats:
        detected_ts = t.get("detected_at") or t.get("detected_after")
        if cutoff_ts is not None and detected_ts is not None:
            if detected_ts < cutoff_ts:
                continue
        detected_str = datetime.datetime.fromtimestamp(detected_ts).strftime("%Y-%m-%d") if detected_ts else ""
        rows.append({
            "mac_address": t.get("mac_address", ""),
            "device_hostname": t.get("device_hostname", "") or t.get("hostname", ""),
            "device_ip": t.get("device_ip", "") or t.get("ip_address", ""),
            "name": t.get("name", ""),
            "severity": t.get("severity", ""),
            "status": t.get("status", ""),
            "detected_at": detected_str,
        })
    if len(threats) < 100:
        break
    page += 1

with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

severity_counter = Counter(r["severity"] for r in rows)
status_counter = Counter(r["status"] for r in rows)

print(json.dumps({
    "total_rows": len(rows),
    "filepath": str(filepath),
    "pages_fetched": page + 1,
    "days_filter": days,
    "severity_distribution": dict(severity_counter),
    "status_distribution": dict(status_counter),
}))
PYEOF
```

Parse the small JSON summary that the script prints.

### 3. Report

Tell the user:
- Total threats exported and active filters applied
- The full path to the CSV file
- Severity and status breakdown
- Any notable observations (e.g., spike in CRITICAL threats, many devices affected)

### 4. Offer to open the CSV

Ask the user if they would like to open the CSV file. If yes, run:
```
open "<filepath>"
```
