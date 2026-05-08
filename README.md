[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Cylera_cylera-cli&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Cylera_cylera-cli) [![Bugs](https://sonarcloud.io/api/project_badges/measure?project=Cylera_cylera-cli&metric=bugs)](https://sonarcloud.io/summary/new_code?id=Cylera_cylera-cli) [![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=Cylera_cylera-cli&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=Cylera_cylera-cli) [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Cylera_cylera-cli&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Cylera_cylera-cli) [![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=Cylera_cylera-cli&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=Cylera_cylera-cli)

# Cylera CLI  

A command-line interface for the [Cylera Partner API](https://github.com/Cylera/cylera-partner-api), providing read-only access to device inventory, threats, vulnerabilities, and network information.

It can be used stand-alone or integrated into an AI workflow using the bundled Claude Code skill (see below).

Alternatively, if you are looking to incorporate the power of Cylera into your AI workflows, you may also consider the [Cylera MCP Server](https://github.com/Cylera/cylera-mcp-server).

This [Cylera AI Integration Options document](CLI_VS_MCP.md) may help you decide which one may make sense depending on your AI workflows.

## Demo
![Demo][demo]

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Credentials for accessing Cylera

## Installation

Use the [uvx](https://docs.astral.sh/uv/guides/tools/) command to invoke a tool without installing it.

```bash
uvx --from cylera-cli cylera --help
```

This is quite long-winded and so if you want to shorten it, the following alias is recommended:

```bash
alias cylera='uvx --from cylera-cli cylera'
```

The rest of the document assumes the alias is set.

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

### 1Password Secrets Management

Alternatively, you can use [1Password CLI](https://developer.1password.com/docs/cli/get-started/)
for secrets management. Set your environment ID and prefix commands with `op run`:

```bash
export OP_ENVIRONMENT_ID=<your-environment-id>
op run --environment "$OP_ENVIRONMENT_ID" -- cylera devices
```

## Usage

```bash
cylera <command> [options]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize Cylera CLI configuration interactively |
| `organization` | Get the organization associated with the current credentials |
| `organizations` | List organizations available to switch into |
| `switchorg` | Switch to a different organization |
| `resetorg` | Reset organization back to home |
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

**List available organizations:**
```bash
cylera organizations
```

**Switch to a different organization:**
```bash
cylera switchorg <organization-id>
```

**Reset back to home organization:**
```bash
cylera resetorg
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

## Claude Code Skill

This repo includes Claude Code skills that drive the CLI for you enabling you to query things in natural language.

See [CODING_AGENT_SKILLS.md](CODING_AGENT_SKILLS.md) for full installation instructions and usage examples.

## License

See LICENSE file for details.

[demo]: demo.webp
