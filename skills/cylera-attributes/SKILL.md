---
name: cylera-attributes
description: Query Cylera devices by attribute label and export results to CSV. Optionally filter by last seen window. Use when the user wants to find devices with a specific attribute (e.g., "TeamViewer", "remote access", "end of life"), optionally seen in the last N days or last week.
argument-hint: <attribute-label> [last N days | last week | Nd]
allowed-tools: Bash, Write, AskUserQuestion
---

Query Cylera for devices matching an attribute label and export the results to a CSV file. Supports an optional last-seen filter.

## Arguments

`$ARGUMENTS` may contain:
- An attribute label (required, partial match supported by the API)
- An optional last-seen window in any of these forms: `last N days`, `last week`, `Nd` (e.g. `7d`, `30d`)

Examples:
- `TeamViewer` — all devices with TeamViewer
- `TeamViewer last 7 days` — only devices seen in the last 7 days
- `TeamViewer last week` — same as last 7 days
- `TeamViewer 30d` — only devices seen in the last 30 days

If no argument is provided, ask the user what attribute label they want to search for. Ask separately if they want to filter by last seen.

## Steps

### 1. Detect credentials and parse arguments (run in parallel if arguments are known)

If `$ARGUMENTS` is provided, run both sub-steps simultaneously. Otherwise, run step 1a first, then ask.

**1a) Detect credentials — single Bash call:**
```
which doppler 2>/dev/null && echo "doppler_found" || ([ -f .env ] && echo "dotenv_found" || echo "none")
```
- `doppler_found` → use `doppler run --` as the command prefix
- `dotenv_found` → use no prefix
- `none` → offer to run `cylera init`. If the user agrees, run it and use no prefix. If they decline, stop.

**1b) Parse arguments:**

Extract the label and optional days filter from `$ARGUMENTS` using these rules:
- Strip trailing patterns like `last N days`, `last week`, `Nd` to get the label
- `last week` → 7 days
- `last N days` or `Nd` → N days
- No pattern → no filter (export all)

### 2. Run the fetch-and-export script

The API response is too large to process in context. Run a single self-contained Python script that handles all pagination, filtering, CSV writing, and path/date computation internally, returning only a small JSON summary.

Substitute `<label>`, `<prefix>`, and `<days>` before running. Set `<days>` to an integer (e.g. `7`) if filtering, or `0` for no filter.

```
<prefix> python3 - << 'PYEOF'
import subprocess, json, csv, sys, datetime
from pathlib import Path
from collections import Counter

label = "<label>"
days = <days>  # 0 means no filter

slug = label.lower().replace(" ", "-")
date = datetime.date.today().isoformat()
cutoff_ts = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp() if days else None
days_suffix = f"-last{days}days" if days else ""
filepath = Path.cwd() / f"cylera-{slug}{days_suffix}-{date}.csv"
columns = ["hostname", "ip_address", "mac_address", "type", "class", "os",
           "vendor", "model", "location", "risk", "vlan", "last_seen",
           "attribute_label", "attribute_value"]

rows = []
page = 0

while True:
    result = subprocess.run(
        ["cylera", "devices", "--attribute-label", label,
         "--page-size", "100", "--page", str(page)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(json.dumps({"error": result.stderr}))
        sys.exit(1)
    data = json.loads(result.stdout)
    devices = data.get("devices", [])
    for device in devices:
        last_seen_ts = device.get("last_seen")
        if cutoff_ts is not None:
            if last_seen_ts is None or last_seen_ts < cutoff_ts:
                continue
        last_seen_str = datetime.datetime.fromtimestamp(last_seen_ts).strftime("%Y-%m-%d") if last_seen_ts else ""
        for attr in device.get("matching_attributes", []):
            rows.append({
                "hostname": device.get("hostname", ""),
                "ip_address": device.get("ip_address", ""),
                "mac_address": device.get("mac_address", ""),
                "type": device.get("type", ""),
                "class": device.get("class", ""),
                "os": device.get("os", ""),
                "vendor": device.get("vendor", ""),
                "model": device.get("model", ""),
                "location": device.get("location", ""),
                "risk": device.get("risk", ""),
                "vlan": device.get("vlan", ""),
                "last_seen": last_seen_str,
                "attribute_label": attr.get("label", ""),
                "attribute_value": attr.get("value", ""),
            })
    if len(devices) < 100:
        break
    page += 1

with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)

risk_counter = Counter(str(r["risk"]) for r in rows)
type_counter = Counter(r["type"] for r in rows)

print(json.dumps({
    "total_rows": len(rows),
    "filepath": str(filepath),
    "pages_fetched": page + 1,
    "days_filter": days,
    "risk_distribution": dict(risk_counter),
    "top_types": type_counter.most_common(5),
}))
PYEOF
```

Parse the small JSON summary that the script prints.

### 3. Report

Tell the user:
- Total records written to the CSV (and the filter window if active, e.g. "seen in the last 7 days")
- The full path to the CSV file
- Any notable observations (e.g., all devices are the same type, high-risk devices present)

### 4. Offer to open the CSV

Ask the user if they would like to open the CSV file. If yes, run:
```
open "<filepath>"
```
