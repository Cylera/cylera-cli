# Cylera CLI  

A command-line interface for the [Cylera Partner API](https://partner.us1.cylera.com/apidocs/), providing read-only access to device inventory, threats, vulnerabilities, and network information.

It can be used stand-alone or integrated into an AI workflow using the bundled Claude Code skill (see below).

Alternatively, if you are looking to incorporate the power of Cylera into your AI workflows, you may also consider the [Cylera MCP Server](https://github.com/Cylera/cylera-mcp-server).

This [Cylera AI Integration Options document](CLI_VS_MCP.md) may help you decide which one may make sense depending on your AI workflows.

## Demo
![Demo][demo]

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Credentials for accessing Cylera

## Installation

Install using [uv](https://docs.astral.sh/uv/):

```bash
uv tool install .
```

Then run commands directly:

```bash
cylera --help
```

To uninstall:

```bash
uv tool uninstall cylera
```

Alternatively, run without installing:

```bash
uvx cylera --help
```

## Configuration

Run the interactive setup to configure your credentials:

```bash
cylera init
```

This will prompt you to:
1. Select your Cylera API endpoint (US, UK, or Demo)
2. Enter your username (email)
3. Enter your password

Credentials are stored in a `.env` file in the current directory.

### Manual Configuration

Alternatively, set environment variables directly:

```bash
export CYLERA_BASE_URL="https://partner.us1.cylera.com/"
export CYLERA_USERNAME="your-email@example.com"
export CYLERA_PASSWORD="your-password"
```

### Doppler Secrets Management

Instead of storing the secrets in a .env file, you may choose to use a secrets
management solution such as [Doppler](https://www.doppler.com).

To use [Doppler](https://www.doppler.com), simply add the following prefix to all commands.

    doppler run -- 

For example, to run "cylera devices" accessing secrets from Doppler, you would
run the following:

    doppler run -- cylera devices

## Usage

```bash
cylera <command> [options]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize Cylera CLI configuration interactively |
| `organization` | Get the organization associated with the current credentials |
| `device` | Get details for a specific device by MAC address |
| `devices` | Get a list of devices with optional filters |
| `deviceattributes` | Get attributes for a device by MAC address |
| `procedures` | Get a list of medical procedures |
| `subnets` | Get a list of network subnets |
| `riskmitigations` | Get mitigations for a specific vulnerability |
| `vulnerabilities` | Get a list of vulnerabilities |
| `threats` | Get a list of detected threats |

#### Organization

**Get organization info:**
```bash
cylera organization
```

#### Device Inventory

**List devices:**
```bash
cylera devices --page-size 10
cylera devices --vendor Philips --class Medical
cylera devices --ip-address 10.40
```

**Get a specific device:**
```bash
cylera device 7f:14:22:72:00:e5
```

**Get device attributes:**
```bash
cylera deviceattributes 7f:14:22:72:00:e5
```

#### Vulnerabilities & Risk

**List vulnerabilities:**
```bash
cylera vulnerabilities --severity CRITICAL
cylera vulnerabilities --status OPEN --page-size 20
```

**Get mitigations for a vulnerability:**
```bash
cylera riskmitigations "Ripple20 (ICSA-20-168-01)"
```

#### Threats

**List threats:**
```bash
cylera threats --severity HIGH
cylera threats --mac-address bb:b0:71:cf:30:0a
```

#### Network

**List subnets:**
```bash
cylera subnets
cylera subnets --vlan 477
```

#### Medical Procedures

**List procedures:**
```bash
cylera procedures --page-size 10
cylera procedures --completed-after 2025/01/01
```

### Common Options

Most list commands support these options:

| Option | Description |
|--------|-------------|
| `--page` | Page number for pagination |
| `--page-size` | Results per page (max 100) |
| `--mac-address` | Filter by device MAC address |
| `--severity` | Filter by severity (INFO, LOW, MEDIUM, HIGH, CRITICAL) |
| `--status` | Filter by status (OPEN, IN_PROGRESS, RESOLVED, SUPPRESSED) |

### Output

All commands output JSON to stdout, which can be piped to tools like `jq`:

```bash
cylera devices --page-size 5 | jq '.devices[].hostname'
```

## Debugging

Enable debug output to see request details:

```bash
DEBUG=1 cylera devices --page-size 1
```

## API Endpoints

The CLI supports these Cylera Partner API regions:

- US: `https://partner.us1.cylera.com/`
- UK: `https://partner.uk1.cylera.com/`
- Demo: `https://partner.demo.cylera.com/`

## Claude Code Skills

This repo includes a Claude Code skill that lets you query devices by attribute and export results to CSV directly from a conversation.

### Install

**macOS / Linux:**
```bash
cp -r skills/cylera-attributes ~/.claude/skills/
```

**Windows (PowerShell):**
```powershell
Copy-Item -Recurse skills\cylera-attributes $env:USERPROFILE\.claude\skills\
```

### Usage

Once installed, use it in any Claude Code session:

```
/cylera-attributes TeamViewer
/cylera-attributes "end of life"
/cylera-attributes
```

The skill handles pagination automatically, writes results to a dated CSV in the current directory, and reports a summary of risk distribution and device types.

## License

See LICENSE file for details.

[demo]: demo.webp
