"""Offline regression checks for the unmerged Agent HQ WhatsApp adapter."""
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from starlette.requests import Request


def incoming(raw, signature=''):
    async def receive():
        return {'type':'http.request', 'body':raw, 'more_body':False}
    return Request({'type':'http', 'method':'POST', 'path':'/webhook',
                    'headers':[(b'x-hub-signature-256',signature.encode())]}, receive)


class HqWebhookTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('hq_webhook_fixture', Path(__file__).parents[1]/'apps/agent-hq/app.py')
        self.hq=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.hq)
        self.temp=tempfile.TemporaryDirectory()
        self.hq.DB_PATH=Path(self.temp.name)/'fixture.sqlite3'
        self.hq.init_db()
        self.env=patch.dict(os.environ, {'WHATSAPP_APP_SECRET':'fictional-test-secret'})
        self.env.start()
        self.net=patch.object(self.hq, 'urlopen', side_effect=AssertionError('Network forbidden in webhook tests'))
        self.net.start()

    def tearDown(self):
        self.net.stop()
        self.env.stop()
        self.temp.cleanup()

    async def deliver(self, raw, valid=True):
        signature='sha256='+hmac.new(b'fictional-test-secret',raw,hashlib.sha256).hexdigest()
        return await self.hq.webhook_receive(incoming(raw, signature if valid else 'sha256=invalid'))

    async def test_invalid_signature_creates_no_message_or_task(self):
        response=await self.deliver(b'{}', valid=False)
        self.assertEqual(response.status_code,401)
        with self.hq.db() as conn:
            for table in ('wa_messages','tasks','notifications'):
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0)

    async def test_duplicate_signed_delivery_creates_one_queue_item(self):
        raw=json.dumps({'entry':[{'changes':[{'value':{'messages':[{
            'id':'fictional-message-1','from':'447700900000','text':{'body':'Review this job offer'}
        }]}}]}]}).encode()
        first=await self.deliver(raw)
        second=await self.deliver(raw)
        self.assertEqual(json.loads(first.body)['messages_stored'],1)
        self.assertEqual(json.loads(second.body)['messages_stored'],0)
        with self.hq.db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM wa_messages').fetchone()[0],1)
            task=conn.execute('SELECT agent_id,status FROM tasks').fetchall()
            self.assertEqual([(r['agent_id'],r['status']) for r in task],[('jobshield','queued')])

    async def test_signed_malformed_json_is_rejected(self):
        self.assertEqual((await self.deliver(b'{')).status_code,400)

    async def test_missing_secret_fails_closed(self):
        with patch.dict(os.environ,{'WHATSAPP_APP_SECRET':''}):
            self.assertEqual((await self.hq.webhook_receive(incoming(b'{}'))).status_code,503)
