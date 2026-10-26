# Security

This repository is a portfolio prototype and uses synthetic demonstration data only. Do not commit passwords, API keys, production credentials, personal data, client evidence or confidential employer information.

If adapting the prototype for real systems, add authentication, authorisation, secure secret storage, tamper-resistant audit storage, input validation, privacy controls, threat modelling and independent security review before production use.

## MCP transport boundary

DNS-rebinding protection is enabled for the Streamable HTTP MCP endpoint. Localhost is allowed for local development. A public deployment must provide its exact hostname through the platform's `RENDER_EXTERNAL_HOSTNAME` or `VERCEL_URL` variable, or through `PALM92_ALLOWED_HOSTS`. Browser origins must be explicitly listed in `PALM92_ALLOWED_ORIGINS`.

Example:

```text
PALM92_ALLOWED_HOSTS=mcp.palm92.example
PALM92_ALLOWED_ORIGINS=https://mcp.palm92.example
```

Do not use a catch-all host. Invalid host and origin configuration fails during application startup.
