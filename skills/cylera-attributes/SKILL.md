---
name: cylera-attributes
description: Query Cylera devices by attribute label and export results to CSV. Use when the user wants to find devices with a specific attribute (e.g., "TeamViewer", "remote access", "end of life").
argument-hint: <attribute-label>
allowed-tools: Bash, Write, AskUserQuestion
---

Query Cylera for devices matching an attribute label and export the results to a CSV file.

## Arguments

`$ARGUMENTS` is the attribute label to search for (partial match supported by the API).
If no argument is provided, ask the user what attribute label they want to search for.

## Steps

### 1. Detect credentials and determine label (run in parallel if label is known)

If `$ARGUMENTS` is provided, run both sub-steps simultaneously. Otherwise, run step 1a first, then ask for the label.

**1a) Detect credentials — single Bash call:**
```
which doppler 2>/dev/null && echo "doppler_found" || ([ -f .env ] && echo "dotenv_found" || echo "none")
```
- `doppler_found` → use `doppler run --` as the command prefix
- `dotenv_found` → use no prefix
- `none` → offer to run `cylera init`. If the user agrees, run it and use no prefix. If they decline, stop.

**1b) Determine the attribute label:**

Use `$ARGUMENTS` if provided, otherwise ask the user.

### 2. Run the fetch-and-export script

The API response is too large to process in context. Run a single self-contained Python script that handles all pagination, CSV writing, and path/date computation internally, returning only a small JSON summary.

```
<prefix> python3 - << 'PYEOF'
import subprocess, json, csv, sys, datetime
from pathlib import Path
from collections import Counter

label = "<label>"
slug = label.lower().replace(" ", "-")
date = datetime.date.today().isoformat()
filepath = Path.cwd() / f"cylera-{slug}-{date}.csv"
columns = ["hostname", "ip_address", "mac_address", "type", "class", "os",
           "vendor", "model", "location", "risk", "vlan", "attribute_label", "attribute_value"]

total_rows = 0
page = 0
risk_counter = Counter()
type_counter = Counter()

with open(filepath, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=columns)
    writer.writeheader()
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
            for attr in device.get("matching_attributes", []):
                writer.writerow({
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
                    "attribute_label": attr.get("label", ""),
                    "attribute_value": attr.get("value", ""),
                })
                total_rows += 1
                risk_counter[str(device.get("risk", "unknown"))] += 1
                type_counter[device.get("type", "unknown")] += 1
        if len(devices) < 100:
            break
        page += 1

print(json.dumps({
    "total_rows": total_rows,
    "filepath": str(filepath),
    "pages_fetched": page + 1,
    "risk_distribution": dict(risk_counter),
    "top_types": type_counter.most_common(5),
}))
PYEOF
```

Only substitute `<label>` (the attribute label string) and `<prefix>` (the command prefix from step 1a). The script computes slug, date, and filepath itself.

Parse the small JSON summary that the script prints.

### 3. Report

Tell the user:
- Total records written to the CSV
- The full path to the CSV file
- Any notable observations (e.g., all devices are the same type, high-risk devices present)

### 4. Offer to open the CSV

Ask the user if they would like to open the CSV file. If yes, run:
```
open "<filepath>"
```
