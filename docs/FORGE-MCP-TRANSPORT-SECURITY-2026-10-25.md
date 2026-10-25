# FORGE evidence: MCP transport security

Date: 25 October 2026

## Verified problem

The public ASGI entry point constructed `TransportSecuritySettings` with DNS-rebinding protection disabled. That removed the MCP SDK's `Host` and `Origin` validation from the Streamable HTTP transport.

## Completed change

- Enabled DNS-rebinding protection.
- Added exact allow-list configuration for public hosts and browser origins.
- Preserved safe localhost patterns for local development.
- Read Render and Vercel deployment host variables without trusting an incoming request.
- Rejected catch-all hosts, URL-shaped hosts and origins containing paths at startup.
- Added nine tests covering the ASGI wiring, configuration and request rejection/acceptance paths.
- Added read-only CI for tests, compilation and dependency auditing.

## Verification boundary

The tests exercise the MCP SDK transport-security middleware directly. They do not prove that a public deployment, proxy or custom domain is configured correctly. No deployment or external communication was performed.

Before public use, set the exact production host and browser origin, deploy through the authorised target, then verify accepted and rejected requests end to end.
