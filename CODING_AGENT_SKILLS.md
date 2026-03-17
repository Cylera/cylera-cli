# Cylera Claude Code Skills

This repo includes Claude Code skills that let you query Cylera data and export results to CSV directly from a conversation — no scripting required.

## Available Skills

| Skill | Description |
|-------|-------------|
| [`/cylera-attributes`](#cylera-attributes) | Find devices by attribute label (e.g. TeamViewer, end of life) |
| [`/cylera-vulnerabilities`](#cylera-vulnerabilities) | Export vulnerabilities filtered by severity and/or status |
| [`/cylera-threats`](#cylera-threats) | Export threats filtered by severity and/or status |
| [`/cylera-devices`](#cylera-devices) | Export device inventory filtered by class, vendor, type, or OS |

All skills handle pagination automatically, write results to a dated CSV in the current directory, and report a summary.

---

## Installation

### macOS / Linux

```bash
cp -r skills/cylera-attributes ~/.claude/skills/
cp -r skills/cylera-vulnerabilities ~/.claude/skills/
cp -r skills/cylera-threats ~/.claude/skills/
cp -r skills/cylera-devices ~/.claude/skills/
```

Or install all at once:

```bash
cp -r skills/* ~/.claude/skills/
```

### Windows (PowerShell)

```powershell
Copy-Item -Recurse skills\cylera-attributes $env:USERPROFILE\.claude\skills\
Copy-Item -Recurse skills\cylera-vulnerabilities $env:USERPROFILE\.claude\skills\
Copy-Item -Recurse skills\cylera-threats $env:USERPROFILE\.claude\skills\
Copy-Item -Recurse skills\cylera-devices $env:USERPROFILE\.claude\skills\
```

---

## Credential Detection

All skills automatically detect how you have Cylera credentials configured and apply the correct prefix:

| Setup | Detection |
|-------|-----------|
| [Doppler](https://www.doppler.com) | `doppler` is in PATH |
| [1Password CLI](https://developer.1password.com/docs/cli/) | `op` is in PATH and `$OP_ENVIRONMENT_ID` is set |
| `.env` file | `.env` exists in the current directory |
| Not configured | Skill offers to run `cylera init` |

---

## Skills

### cylera-attributes

Find devices that have a specific attribute label and export them to CSV.

**Usage:**
```
/cylera-attributes <attribute-label> [filter]
```

**Examples:**
```
/cylera-attributes TeamViewer
/cylera-attributes "end of life"
/cylera-attributes TeamViewer last 7 days
/cylera-attributes "remote access" 30d
```

**Output columns:** `hostname`, `ip_address`, `mac_address`, `serial_number`, `type`, `class`, `os`, `vendor`, `model`, `location`, `risk`, `vlan`, `last_seen`, `attribute_label`, `attribute_value`

**Summary includes:** total rows, unique device count, risk distribution, top device types

---

### cylera-vulnerabilities

Export vulnerabilities to CSV with optional severity, status, and detection window filters.

**Usage:**
```
/cylera-vulnerabilities [severity] [status] [filter]
```

**Severity values:** `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
**Status values:** `OPEN`, `IN_PROGRESS`, `RESOLVED`, `SUPPRESSED`

**Examples:**
```
/cylera-vulnerabilities
/cylera-vulnerabilities CRITICAL
/cylera-vulnerabilities CRITICAL OPEN
/cylera-vulnerabilities HIGH last 30 days
/cylera-vulnerabilities OPEN 7d
```

**Output columns:** `mac_address`, `device_hostname`, `device_ip`, `name`, `severity`, `confidence`, `status`, `detected_at`

**Summary includes:** total count, severity distribution, status distribution

---

### cylera-threats

Export detected threats to CSV with optional severity, status, and detection window filters.

**Usage:**
```
/cylera-threats [severity] [status] [filter]
```

**Severity values:** `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
**Status values:** `OPEN`, `IN_PROGRESS`, `RESOLVED`, `SUPPRESSED`

**Examples:**
```
/cylera-threats
/cylera-threats HIGH
/cylera-threats CRITICAL OPEN
/cylera-threats HIGH last 30 days
/cylera-threats OPEN 7d
```

**Output columns:** `mac_address`, `device_hostname`, `device_ip`, `name`, `severity`, `status`, `detected_at`

**Summary includes:** total count, severity distribution, status distribution

---

### cylera-devices

Export device inventory to CSV with optional filters for class, type, vendor, or OS.

**Usage:**
```
/cylera-devices [class <value>] [type <value>] [vendor <value>] [os <value>]
```

**Examples:**
```
/cylera-devices
/cylera-devices Medical
/cylera-devices vendor Philips
/cylera-devices vendor GE class Medical
/cylera-devices os Windows
```

**Output columns:** `hostname`, `ip_address`, `mac_address`, `serial_number`, `type`, `class`, `os`, `vendor`, `model`, `location`, `risk`, `vlan`, `last_seen`, `first_seen`

**Summary includes:** total device count, class distribution, top vendors, top device types
