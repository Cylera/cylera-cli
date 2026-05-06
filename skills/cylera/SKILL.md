---
name: cylera
description: General-purpose Cylera API skill covering all CLI commands. Use for any Cylera query in natural language — device lookups by MAC/IP/vendor/OS/class, threat and vulnerability investigation, subnet browsing, medical procedure queries, org management, risk mitigations, and multi-step device profiles.
argument-hint: <natural language query, e.g. "all Philips medical devices" or "CRITICAL open threats last 30 days" or "investigate device AA:BB:CC:DD:EE:FF">
allowed-tools: Bash, Write, AskUserQuestion
---

Handle any Cylera API query from natural language. Route to the right API call, auto-paginate, and display results inline or export to CSV based on size and intent.

## Step 1: Detect credentials

Run this single Bash call first:

```bash
([ -f .env ] && echo "dotenv_found") || \
(which op 2>/dev/null && [ -n "$OP_ENVIRONMENT_ID" ] && echo "op_found") || \
(which doppler 2>/dev/null && echo "doppler_found") || \
echo "none"
```

- `dotenv_found` → prefix = (empty string)
- `op_found` → prefix = `op run --environment "$OP_ENVIRONMENT_ID" --`
- `doppler_found` → prefix = `doppler run --`
- `none` → tell the user: "Cylera credentials are not configured. Please run `uvx --from cylera-cli cylera init` in your terminal to set up your credentials." Then stop.

## Step 2: Parse intent from $ARGUMENTS

### Command routing

| Intent | Command | Notes |
|--------|---------|-------|
| "my org", "current org", "what org" | `organization` | No args |
| "list orgs", "available orgs", "all orgs", "orgs" | `organizations` | No args |
| "switch org", "switch to org", "change org" | `switchorg <org_id>` | Extract org ID if present; otherwise look up by name — see Step 3d |
| "reset org", "home org", "go back to home" | `resetorg` | No args |
| MAC address + "details"/"info"/"get"/"look up", or bare MAC address | `device <mac>` | Point lookup |
| "attributes for" + MAC, "device attributes", "what attributes" | `deviceattributes <mac>` | Point lookup |
| "investigate", "profile", "full details", "everything about" + device | Investigation chain | See Step 3c |
| "mitigations for", "remediate", "how to fix", "fix" + name | `riskmitigations <name>` | Point lookup; extract vuln name as remaining text |
| "subnets", "subnet", "network subnets", "vlans" | `subnets` | List query |
| "procedures", "medical procedures" | `procedures` | List query |
| "vulnerabilities", "vulns", "CVEs", "CVE-" | `vulnerabilities` | List query |
| "threats", "detected threats" | `threats` | List query |
| "devices", "inventory", "find devices", "show devices" | `devices` | List query |
| Ambiguous | Ask the user which entity they want | |

### Filter extraction (list queries)

Extract these from $ARGUMENTS and map to API kwargs:

| Value pattern | API kwarg | Applies to |
|--------------|-----------|------------|
| INFO / LOW / MEDIUM / HIGH / CRITICAL (case-insensitive) | `severity` | threats, vulnerabilities |
| OPEN / IN_PROGRESS / RESOLVED / SUPPRESSED (case-insensitive) | `status` | threats, vulnerabilities |
| LOW / MEDIUM / HIGH after "confidence" | `confidence` | vulnerabilities only |
| MAC address (6 hex groups separated by `:`) | `mac_address` | threats, vulnerabilities, devices |
| IP pattern (dotted decimal, partial OK) | `ip_address` | devices |
| Medical / Infrastructure / IoT / or explicit "class" keyword | `device_class` | devices |
| Device type noun (X-Ray, EEG, Ultrasound, Infusion Pump, etc.) | `device_type` | devices |
| Vendor proper noun (Philips, GE, Siemens, Baxter, etc.) | `vendor` | devices |
| OS name (Windows, Linux, etc.) | `os` | devices |
| Text after "attribute" / "with attribute" | `attribute_label` | devices |
| CIDR notation (e.g. `10.1.0.0/24`) | `cidr_range` | subnets |
| Number after "vlan" | `vlan` | subnets |
| Text after "named" / "called" / "name" | `name` | threats, vulnerabilities |

### Date/time conversion

Convert relative date expressions to epoch timestamps (integer seconds since Unix epoch):

- "last N days" / "Nd" / "past N days" → cutoff_epoch = int((now − N days).timestamp())
- "last week" → N = 7
- "last month" → N = 30
- "since YYYY-MM-DD" → parse and convert to epoch
- "today" → midnight of today
- No date expression → no timestamp filter (cutoff_epoch = None)

For **devices**: use `last_seen_after=<epoch>` kwarg
For **threats** and **vulnerabilities**: use `detected_after=<epoch>` kwarg
For **procedures**: use `completed_after="YYYY/MM/DD"` (string, not epoch)
For **subnets**: no date filter available

### Output mode

- If $ARGUMENTS contains "export", "csv", "download", "save to file", "write" → `export_mode = True`
- Otherwise → `export_mode = False` (display inline; offer export if total > 20)

---

## Step 3: Execute

### 3a. Point lookups

For `organization`, `organizations`, `resetorg`, `device <mac>`, `deviceattributes <mac>`, `riskmitigations <name>`, `switchorg <org_id>`:

Run directly via the CLI:
```bash
<prefix> uvx --from cylera-cli cylera <command> [<arg>]
```

Present the result as a readable markdown summary — never raw JSON. Key fields to surface:

- **device**: hostname, IP, MAC, vendor, model, type, class, OS, location, risk score, last_seen (human date)
- **deviceattributes**: each attribute label + value as a bullet list
- **organization**: org name and ID
- **organizations**: table of org ID | name
- **riskmitigations**: numbered list of mitigation steps

### 3b. List queries

For `devices`, `threats`, `vulnerabilities`, `subnets`, `procedures`, use `uv run` to execute a single Python process that calls the `cylera_client` API directly. This avoids launching a subprocess per page and is significantly faster for large result sets.

Before running, substitute these values directly into the Python source:
- `ENTITY` → one of: `"devices"` / `"threats"` / `"vulnerabilities"` / `"subnets"` / `"procedures"`
- `FILTERS` → Python dict of API kwargs with non-None values only, e.g. `{"device_class": "Medical", "vendor": "Philips"}`
- `CUTOFF_TS` → float epoch or `None` (for post-fetch date filtering when the API doesn't accept a timestamp directly)
- `DATE_FIELD` → response field used for post-fetch filtering, or `None`
  - devices → `"last_seen"`, threats → `"detected_at"`, vulnerabilities → `"detected_at"`, subnets/procedures → `None`
- `EXPORT_MODE` → `True` or `False`
- `COLUMNS` → Python list of field names (use defaults below)

**Default columns:**
- devices: `["hostname", "ip_address", "mac_address", "vendor", "model", "type", "class", "os", "location", "risk", "vlan", "last_seen", "first_seen"]`
- threats: `["mac_address", "device_hostname", "device_ip", "name", "severity", "status", "detected_at"]`
- vulnerabilities: `["mac_address", "device_hostname", "device_ip", "name", "severity", "confidence", "status", "detected_at"]`
- subnets: `["cidr_range", "description", "vlan", "device_count"]`
- procedures: `["device_uuid", "procedure_name", "accession_number", "completed_at"]`

```bash
<prefix> uv run --with cylera-cli python3 - << 'PYEOF'
import os, json, csv, datetime, sys
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv

if not os.environ.get('CYLERA_BASE_URL'):
    load_dotenv(Path.cwd() / '.env')

from cylera_client import CyleraClient, Inventory, Risk, Threat, Network, Utilization

entity      = ENTITY       # e.g. "devices"
filters     = FILTERS      # e.g. {"device_class": "Medical", "vendor": "Philips"}
cutoff_ts   = CUTOFF_TS    # e.g. 1743292800.0 or None
date_field  = DATE_FIELD   # e.g. "last_seen" or None
export_mode = EXPORT_MODE  # True or False
columns     = COLUMNS      # list of field names

client = CyleraClient(
    username=os.environ['CYLERA_USERNAME'],
    password=os.environ['CYLERA_PASSWORD'],
    base_url=os.environ['CYLERA_BASE_URL'],
)

api_map = {
    'devices':         (Inventory,   'get_devices',        'devices'),
    'threats':         (Threat,      'get_threats',        'threats'),
    'vulnerabilities': (Risk,        'get_vulnerabilities','vulnerabilities'),
    'subnets':         (Network,     'get_subnets',        'subnets'),
    'procedures':      (Utilization, 'get_procedures',     'procedures'),
}

cls, method, result_key = api_map[entity]
api = cls(client)

rows = []
page = 0

while True:
    result = getattr(api, method)(page=page, page_size=100, **filters)
    items = result.get(result_key, [])
    for item in items:
        if cutoff_ts and date_field:
            ts = item.get(date_field)
            if ts is None or ts < cutoff_ts:
                continue
        for field in ('last_seen', 'first_seen', 'detected_at', 'completed_at'):
            if field in item and isinstance(item[field], (int, float)):
                item[field] = datetime.datetime.fromtimestamp(item[field]).strftime('%Y-%m-%d')
        rows.append(item)
    if len(items) < 100:
        break
    page += 1

client.close()

date_str = datetime.date.today().isoformat()
slug = '_'.join(f'{k}_{v}' for k, v in filters.items()) or 'all'
filepath = Path.cwd() / f'cylera-{entity}-{slug}-{date_str}.csv'

if export_mode:
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, '') for c in columns})

stat_fields = [c for c in columns if c in ('severity', 'status', 'class', 'vendor', 'type', 'os', 'confidence', 'risk', 'vlan')]
distributions = {}
for field in stat_fields[:4]:
    counter = Counter(str(r.get(field, '')) for r in rows)
    distributions[field] = dict(counter.most_common(10))

print(json.dumps({
    'total': len(rows),
    'pages_fetched': page + 1,
    'filepath': str(filepath) if export_mode else None,
    'distributions': distributions,
    'preview': rows[:20],
    'export_mode': export_mode,
}))
PYEOF
```

### 3c. Investigation chain

When intent is "investigate", "full profile", or "everything about" a device, run four sequential Bash calls:

```bash
<prefix> uvx --from cylera-cli cylera device <mac>
<prefix> uvx --from cylera-cli cylera deviceattributes <mac>
<prefix> uvx --from cylera-cli cylera threats --mac-address <mac> --page-size 100
<prefix> uvx --from cylera-cli cylera vulnerabilities --mac-address <mac> --page-size 100
```

If $ARGUMENTS contains an IP address instead of a MAC, first run:
```bash
<prefix> uvx --from cylera-cli cylera devices --ip-address <ip> --page-size 10
```
Extract the MAC from the first result, then proceed with the four calls above.

Synthesize all results into a structured report with these sections:
1. **Device Profile** — hostname, IP, vendor, model, type, class, OS, location, risk, first/last seen
2. **Attributes** — bullet list of label: value pairs
3. **Threats** — count by severity/status; table of OPEN/IN_PROGRESS items
4. **Vulnerabilities** — count by severity/status; table of OPEN/IN_PROGRESS items
5. **Summary** — overall risk posture, notable findings, recommended next steps

### 3d. switchorg — name-to-ID lookup

If $ARGUMENTS contains a bare UUID-style org ID, run directly:
```bash
<prefix> uvx --from cylera-cli cylera switchorg <org_id>
```

If $ARGUMENTS contains an org name (e.g. "switch to Acme" or "change to the UK org") but no ID, first fetch the org list:
```bash
<prefix> uvx --from cylera-cli cylera organizations
```
Parse the JSON response to find an org whose name case-insensitively matches (or contains) the name from $ARGUMENTS. If exactly one match, use its ID:
```bash
<prefix> uvx --from cylera-cli cylera switchorg <matched_org_id>
```
If zero matches, tell the user no org matched and display the full org list.
If multiple matches, show the matching orgs and ask the user to confirm which one.

---

## Step 4: Format and report

**Total ≤ 20 or point lookup**: Display all results as a markdown table or structured list inline.

**Total > 20 and `export_mode = False`**: Show distributions and a preview table of the first 20 rows, then ask:
> "Found N results. Would you like me to: **(a)** export all to CSV, **(b)** filter further, or **(c)** show the full list here?"

**`export_mode = True`**: Report the filepath, total count, and distribution summary. Offer to open:
```bash
open "<filepath>"
```

**Always include**:
- Total count and active filters applied
- Distribution breakdown (e.g. severity split, top vendors, class breakdown)
- Any notable pattern: e.g. "87% OPEN", "all from one vendor", "no Medical devices have OS data"
