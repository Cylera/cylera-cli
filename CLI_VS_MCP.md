# Cylera AI Integration Options

Cylera offers two ways to bring AI assistance into your security and device management workflows: the **[Cylera MCP Server](https://github.com/Cylera/cylera-mcp-server)** and the **[Cylera CLI](https://github.com/Cylera/cylera-cli)**. They are complementary tools designed for different use cases.

Both are built using the [Cylera Client](https://github.com/Cylera/cylera-client) and access the same data through the [Cylera Partner API](https://partner.us1.cylera.com/apidocs/). The choice between them is purely about workflow and interface — not data availability or fidelity.

---

## Cylera MCP Server

The [Cylera MCP Server](https://github.com/Cylera/cylera-mcp-server) exposes Cylera platform capabilities as structured tools that AI assistants can call directly. Given a device identifier, it returns attributes, vulnerabilities, threats, and other device-level data in a typed, structured format — ready to be reasoned over without additional parsing.

This makes it a natural fit for **reactive, investigation-driven workflows**. A threat alert fires, an analyst asks the AI to investigate, and the MCP server enriches the device of interest with full context inline, without leaving the workflow.

The [Cylera MCP Server](https://github.com/Cylera/cylera-mcp-server) is compatible with any MCP-capable AI client — Claude Code, Claude Desktop, and Claude.ai — making it the most portable of the two integrations.

---

## Cylera CLI

The [Cylera CLI](https://github.com/Cylera/cylera-cli) is a command-line tool for interacting with the Cylera platform. It comes bundled with a [Claude Code skill](https://support.claude.com/en/articles/12512176-what-are-skills) called **cylera-attributes**, which instructs Claude Code to use the CLI to query devices by attribute label, paginate through the full results, and export them to a CSV file.

This makes it a natural fit for **proactive, audit-driven workflows**. Security teams can answer questions like "which devices in our inventory have remote access tools installed?" or "show me all end-of-life devices" — and get a timestamped, shareable export in return.

The cylera-attributes skill requires Claude Code and is not available in Claude Desktop or Claude.ai.

---

## Choosing the Right Tool

| Scenario | Best Tool |
|---|---|
| Investigate a specific device flagged in an alert | MCP Server |
| Enrich a device mid-investigation with full context | MCP Server |
| Audit all devices with a specific attribute | CLI + cylera-attributes skill |
| Generate an inventory-wide exposure report | CLI + cylera-attributes skill |
| Works with Claude Desktop or Claude.ai | MCP Server |
| Works with Claude Code | Both |

---

## Using Both Together

The two tools are most powerful in combination. A typical workflow might start with the **cylera-attributes skill** to identify all high-risk devices with a given attribute, then shift to the **MCP Server** to deep-dive on a specific device of concern — pulling full vulnerability detail, threat history, and attribute context within an AI-assisted investigation session.

---

*For more information on deploying either integration, contact your Cylera account team.*
