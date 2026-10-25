import os
import unittest
from unittest.mock import patch

from mcp.server.transport_security import TransportSecurityMiddleware
from starlette.requests import Request

from src.transport_security import build_transport_security


def request(headers: dict[str, str]) -> Request:
    encoded = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    return Request({"type": "http", "method": "POST", "path": "/mcp", "headers": encoded})


class TransportSecurityTests(unittest.IsolatedAsyncioTestCase):
    def settings(self, **environment: str):
        with patch.dict(os.environ, environment, clear=True):
            return build_transport_security()

    def test_protection_is_enabled_with_local_defaults(self):
        settings = self.settings()
        self.assertTrue(settings.enable_dns_rebinding_protection)
        self.assertIn("localhost:*", settings.allowed_hosts)
        self.assertNotIn("*", settings.allowed_hosts)

    def test_asgi_entry_point_uses_protected_settings(self):
        import app

        self.assertTrue(app.security.enable_dns_rebinding_protection)

    def test_deployment_hosts_and_origins_are_explicitly_allowed(self):
        settings = self.settings(
            RENDER_EXTERNAL_HOSTNAME="palm92-governed-agent-mcp.onrender.com",
            VERCEL_URL="palm92-governed-agent-mcp.vercel.app",
            PALM92_ALLOWED_HOSTS="mcp.palm92.example",
            PALM92_ALLOWED_ORIGINS="https://mcp.palm92.example",
        )
        self.assertIn("palm92-governed-agent-mcp.onrender.com", settings.allowed_hosts)
        self.assertIn("palm92-governed-agent-mcp.vercel.app", settings.allowed_hosts)
        self.assertIn("mcp.palm92.example", settings.allowed_hosts)
        self.assertIn("https://mcp.palm92.example", settings.allowed_origins)

    def test_unsafe_wildcard_host_is_rejected_at_startup(self):
        with self.assertRaises(RuntimeError):
            self.settings(PALM92_ALLOWED_HOSTS="*")

    def test_origin_with_path_is_rejected_at_startup(self):
        with self.assertRaises(RuntimeError):
            self.settings(PALM92_ALLOWED_ORIGINS="https://mcp.palm92.example/path")

    async def test_untrusted_host_is_rejected(self):
        middleware = TransportSecurityMiddleware(self.settings())
        response = await middleware.validate_request(
            request({"host": "attacker.example", "content-type": "application/json"}),
            is_post=True,
        )
        self.assertEqual(response.status_code, 421)

    async def test_untrusted_origin_is_rejected(self):
        middleware = TransportSecurityMiddleware(
            self.settings(PALM92_ALLOWED_HOSTS="mcp.palm92.example")
        )
        response = await middleware.validate_request(
            request(
                {
                    "host": "mcp.palm92.example",
                    "origin": "https://attacker.example",
                    "content-type": "application/json",
                }
            ),
            is_post=True,
        )
        self.assertEqual(response.status_code, 403)

    async def test_configured_host_and_origin_are_accepted(self):
        middleware = TransportSecurityMiddleware(
            self.settings(
                PALM92_ALLOWED_HOSTS="mcp.palm92.example",
                PALM92_ALLOWED_ORIGINS="https://mcp.palm92.example",
            )
        )
        response = await middleware.validate_request(
            request(
                {
                    "host": "mcp.palm92.example",
                    "origin": "https://mcp.palm92.example",
                    "content-type": "application/json; charset=utf-8",
                }
            ),
            is_post=True,
        )
        self.assertIsNone(response)

    async def test_post_requires_json_content_type(self):
        middleware = TransportSecurityMiddleware(self.settings())
        response = await middleware.validate_request(
            request({"host": "localhost:8000", "content-type": "text/plain"}),
            is_post=True,
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
