# Deployment

## Target architecture

The deployed portfolio version exposes one ASGI application:

- `/` — visual reviewer interface
- `/api/evaluate` — synthetic governance evaluation used by the demo
- `/mcp` — real Streamable HTTP MCP endpoint
- `/health` — deployment health check

The MCP endpoint exposes governed tools only. External consequential execution remains simulated.

## Required transport configuration

The MCP transport validates `Host`, `Origin` and JSON content type. Localhost is available by default for development. For a public deployment, allow only the exact public hostname and browser origin:

```text
PALM92_ALLOWED_HOSTS=mcp.palm92.example
PALM92_ALLOWED_ORIGINS=https://mcp.palm92.example
```

Render's `RENDER_EXTERNAL_HOSTNAME` and Vercel's `VERCEL_URL` are also read automatically. Custom domains still need the explicit Palm92 variables. Keep these values server-side with the deployment configuration. The application rejects `*`, URL-shaped host entries and origins containing a path.

## Recommended deployment

Vercel supports Python ASGI/FastAPI-style applications. The repository now includes `app.py` as the deployment entry point.

### Local check

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Then verify:

```text
http://localhost:8000/
http://localhost:8000/health
http://localhost:8000/mcp
```

### Portfolio claim after successful public deployment

Safe wording:

> Deployed a public Agentic AI governance reference prototype exposing a Streamable HTTP MCP endpoint and reviewer interface, with deterministic policy gates, evidence traceability, human approval and structured audit records. Consequential external actions are simulated by design.

Do not claim production-scale compliance, live payment execution, or enterprise security certification.
