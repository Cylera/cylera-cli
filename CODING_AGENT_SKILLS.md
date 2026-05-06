# Cylera Claude Code Skill

This repo includes a Claude Code skill that lets you query Cylera data directly from a conversation — no scripting required.

## Installation

Open this repo in Claude Code and say:

> Install or update the skills for me

Claude will copy the skill to the right place. No manual steps needed.

The only other setup required is Cylera credentials. If not already configured, the skill will detect this and offer to run `cylera init`.

---

## Credential Detection

| Setup | Detection |
|-------|-----------|
| [Doppler](https://www.doppler.com) | `doppler` is in PATH |
| [1Password CLI](https://developer.1password.com/docs/cli/) | `op` is in PATH and `$OP_ENVIRONMENT_ID` is set |
| `.env` file | `.env` exists in the current directory |
| Not configured | Skill offers to run `cylera init` |

---

## `/cylera`

General-purpose skill covering all Cylera API commands. Accepts natural language — no need to know CLI flags or API parameters.

For large result sets it displays a summary and preview inline, then offers to export to CSV. For small result sets (≤ 20) it displays results as a table. For a single device it renders a formatted profile.

**Examples:**
```
/cylera all Philips medical devices seen in the last 30 days
/cylera CRITICAL open threats from the last 7 days
/cylera open vulnerabilities for MAC aa:bb:cc:dd:ee:ff
/cylera investigate device aa:bb:cc:dd:ee:ff
/cylera subnets on vlan 100
/cylera mitigations for Log4Shell
/cylera what org am I in
/cylera switch to the Acme org
/cylera list available orgs
/cylera export all Windows devices to CSV
```
