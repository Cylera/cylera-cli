---
name: cylera-devices
description: Export Cylera device inventory to CSV with optional filters for class, type, vendor, or OS. Use when the user wants a full or filtered device inventory snapshot, e.g. "all Medical devices", "all Philips devices", or "devices running Windows".
argument-hint: [class <value>] [type <value>] [vendor <value>] [os <value>]
allowed-tools: Bash, Write, AskUserQuestion
---

Query Cylera for device inventory and export the results to a CSV file. Supports optional filters for device class, type, vendor, and OS.

## Arguments

`$ARGUMENTS` may contain any combination of:
- `class <value>` — device class (e.g. `Medical`, `Infrastructure`)
- `type <value>` — device type (e.g. `X-Ray`, `EEG`, `Infusion Pump`)
- `vendor <value>` — device vendor (e.g. `Philips`, `GE`)
- `os <value>` — operating system (e.g. `Windows`, `Linux`)

Examples:
- (empty) — full inventory
- `Medical` — all Medical class devices
- `vendor Philips` — all Philips devices
- `vendor GE class Medical` — GE medical devices
- `os Windows` — all Windows devices

If no arguments are provided, ask the user if they want to filter or export everything.

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
- If a token matches `class`, `type`, `vendor`, or `os` (case-insensitive), treat the next token as its value
- A bare word that doesn't follow a keyword is treated as a `class` value (common shorthand, e.g. `Medical`)
- Unknown tokens: ignore

### 2. Run the fetch-and-export script

Substitute `CLASS`, `TYPE`, `VENDOR`, `OS`, and `PREFIX` before running. Use empty string for unused filters.

```bash
PREFIX="<prefix>" python3 - << 'PYEOF'
import subprocess, json, csv, sys, datetime, os
from pathlib import Path
from collections import Counter

device_class = "<class>"   # e.g. "Medical" or ""
device_type = "<type>"     # e.g. "X-Ray" or ""
vendor = "<vendor>"        # e.g. "Philips" or ""
device_os = "<os>"         # e.g. "Windows" or ""
prefix = os.environ.get("PREFIX", "").split() if os.environ.get("PREFIX") else []

date = datetime.date.today().isoformat()

parts = []
if device_class:
    parts.append(device_class.lower().replace(" ", "-"))
if device_type:
    parts.append(device_type.lower().replace(" ", "-"))
if vendor:
    parts.append(vendor.lower().replace(" ", "-"))
if device_os:
    parts.append(device_os.lower().replace(" ", "-"))
slug = "-".join(parts) if parts else "all"
filepath = Path.cwd() / f"cylera-devices-{slug}-{date}.csv"

columns = ["hostname", "ip_address", "mac_address", "serial_number",
           "type", "class", "os", "vendor", "model",
           "location", "risk", "vlan", "last_seen", "first_seen"]

cmd = prefix + ["cylera", "devices", "--page-size", "100"]
if device_class:
    cmd += ["--class", device_class]
if device_type:
    cmd += ["--type", device_type]
if vendor:
    cmd += ["--vendor", vendor]
if device_os:
    cmd += ["--os", device_os]

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
    devices = data.get("devices", [])
    for d in devices:
        last_seen_ts = d.get("last_seen")
        first_seen_ts = d.get("first_seen")
        last_seen_str = datetime.datetime.fromtimestamp(last_seen_ts).strftime("%Y-%m-%d") if last_seen_ts else ""
        first_seen_str = datetime.datetime.fromtimestamp(first_seen_ts).strftime("%Y-%m-%d") if first_seen_ts else ""
        rows.append({
            "hostname": d.get("hostname", ""),
            "ip_address": d.get("ip_address", ""),
            "mac_address": d.get("mac_address", ""),
            "serial_number": d.get("serial_number", ""),
            "type": d.get("type", ""),
            "class": d.get("class", ""),
            "os": d.get("os", ""),
            "vendor": d.get("vendor", ""),
            "model": d.get("model", ""),
            "location": d.get("location", ""),
            "risk": d.get("risk", ""),
            "vlan": d.get("vlan", ""),
            "last_seen": last_seen_str,
            "first_seen": first_seen_str,
        })
    if len(devices) < 100:
        break
    page += 1

with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

class_counter = Counter(r["class"] for r in rows)
vendor_counter = Counter(r["vendor"] for r in rows)
type_counter = Counter(r["type"] for r in rows)

print(json.dumps({
    "total_devices": len(rows),
    "filepath": str(filepath),
    "pages_fetched": page + 1,
    "class_distribution": dict(class_counter),
    "top_vendors": vendor_counter.most_common(5),
    "top_types": type_counter.most_common(5),
}))
PYEOF
```

Parse the small JSON summary that the script prints.

### 3. Report

Tell the user:
- Total devices exported and active filters applied
- The full path to the CSV file
- Class, top vendor, and top device type breakdown
- Any notable observations (e.g., large number of unclassified devices, dominant vendor)

### 4. Offer to open the CSV

Ask the user if they would like to open the CSV file. If yes, run:
```
open "<filepath>"
```
