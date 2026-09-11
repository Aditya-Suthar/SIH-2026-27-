"""Run from sih_backend: python -m unittest discover -s tests -v.
No live providers or PostgreSQL are contacted; test-only engine substitution.
"""
import asyncio
import importlib
import io
import json
import logging
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select, func
from sqlalchemy.pool import StaticPool

from app import ai_service as service

GOOD = dict(distress_score=65, risk_level='high', emotions=['fear'],
            requires_attention=True, reason='The message expresses fear and difficulty sleeping.')
MESSAGE = 'Private test message: I feel scared and cannot sleep.'
ENV = {'GEMINI_API_KEY': 'test-secret-gemini', 'GROQ_API_KEY': 'test-secret-groq',
       'OPENROUTER_API_KEY': 'test-secret-openrouter', 'GEMINI_MODEL': 'gemini-2.5-flash-lite',
       'GROQ_MODEL': 'openai/gpt-oss-20b', 'OPENROUTER_MODEL': 'openrouter/free',
       'AI_TEST_ENDPOINT_ENABLED': 'true'}


def reply(request, raw=None, finish=None):
    raw = json.dumps(GOOD) if raw is None else raw
    if request.url.host == 'generativelanguage.googleapis.com':
        return httpx.Response(200, json={'candidates': [{'finishReason': finish or 'STOP',
            'content': {'parts': [{'text': raw}]}}]})
    return httpx.Response(200, json={'choices': [{'finish_reason': finish or 'stop',
                                                'message': {'content': raw}}]})


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)

    async def test_each_provider_normalizes_and_stops(self):
        for winner, name in enumerate(('gemini', 'groq', 'openrouter')):
            seen = []
            def handler(req):
                seen.append(req)
                return reply(req) if len(seen) == winner + 1 else httpx.Response(429)
            result = await service.analyze_distress(MESSAGE, transport=httpx.MockTransport(handler))
            self.assertEqual(result.model_dump(), dict(GOOD, provider=name))
            self.assertEqual(len(seen), winner + 1)
            self.assertEqual([r.url.host for r in seen],
                ['generativelanguage.googleapis.com', 'api.groq.com', 'openrouter.ai'][:winner+1])
            for req in seen:
                self.assertNotIn('test-secret', str(req.url))
                body = json.loads(req.content)
                self.assertNotIn('test-secret', req.content.decode())
                if req.url.host == 'generativelanguage.googleapis.com':
                    self.assertEqual(req.headers['x-goog-api-key'], ENV['GEMINI_API_KEY'])
                    self.assertEqual(body['contents'][0]['parts'][0]['text'], MESSAGE)
                else:
                    self.assertEqual(body['messages'][1]['content'], MESSAGE)
                    self.assertEqual(body['messages'][0]['content'], service.SYSTEM_PROMPT)

    async def test_failure_classes_fall_back(self):
        for kind in ('timeout', 'connect', '401', '403', '429', '500', '503', 'outer_json',
                     'inner_json', 'schema', 'missing_content', 'truncated', 'blocked', 'oversized'):
            with self.subTest(kind=kind):
                seen = []
                def handler(req):
                    seen.append(req)
                    if len(seen) > 1:
                        return reply(req)
                    if kind == 'timeout': raise httpx.ReadTimeout('test-secret-gemini ' + MESSAGE)
                    if kind == 'connect': raise httpx.ConnectError('test-secret-gemini ' + MESSAGE)
                    if kind.isdigit(): return httpx.Response(int(kind), text=MESSAGE + 'test-secret-gemini')
                    if kind == 'outer_json': return httpx.Response(200, text='invalid')
                    if kind == 'inner_json': return reply(req, '{bad json')
                    if kind == 'schema': return reply(req, json.dumps(dict(GOOD, distress_score='65')))
                    if kind == 'missing_content': return httpx.Response(200, json={})
                    if kind == 'truncated': return reply(req, finish='MAX_TOKENS')
                    if kind == 'blocked': return reply(req, finish='SAFETY')
                    return httpx.Response(200, text='x' * 70000)
                result = await service.analyze_distress(MESSAGE, transport=httpx.MockTransport(handler))
                self.assertEqual(result.provider, 'groq')
                self.assertEqual(len(seen), 2)

    async def test_all_fail_safe_logs(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logging.getLogger().addHandler(handler)
        self.addCleanup(logging.getLogger().removeHandler, handler)
        def fail(req):
            raise httpx.ConnectError(MESSAGE + ' '.join(ENV.values()))
        with self.assertRaises(service.AIServiceUnavailable) as ctx:
            await service.analyze_distress(MESSAGE, transport=httpx.MockTransport(fail))
        output = stream.getvalue() + str(ctx.exception)
        self.assertIn('connection_error', output)
        self.assertNotIn(MESSAGE, output)
        self.assertNotIn('test-secret', output)
        self.assertEqual(str(ctx.exception), 'AI analysis is temporarily unavailable.')

    async def test_invalid_client_input_never_calls_providers(self):
        def unexpected(req): self.fail('Provider contacted for invalid input')
        for value in ('', ' \n\t ', 'x'*4001, None, 5, True):
            with self.subTest(value_type=type(value).__name__), self.assertRaises(ValidationError):
                await service.analyze_distress(value, transport=httpx.MockTransport(unexpected))

    async def test_missing_keys_skipped(self):
        with patch.dict(os.environ, {key: '' for key in ENV if key.endswith('_API_KEY')}):
            with self.assertRaises(service.AIServiceUnavailable):
                await service.analyze_distress(MESSAGE, transport=httpx.MockTransport(lambda req: self.fail('Network used')))

    async def test_paid_openrouter_override_not_sent(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': '', 'GROQ_API_KEY': '', 'OPENROUTER_MODEL': 'paid/model'}):
            with self.assertRaises(service.AIServiceUnavailable):
                await service.analyze_distress(MESSAGE, transport=httpx.MockTransport(lambda req: self.fail('Paid request')))

    async def test_wall_timeout_fallback(self):
        real_wait = asyncio.wait_for
        async def short_wait(awaitable, timeout):
            self.assertEqual(timeout, 10)
            return await real_wait(awaitable, timeout=0.02)
        async def handler(req):
            if req.url.host == 'generativelanguage.googleapis.com':
                await asyncio.sleep(1)
            return reply(req)
        with patch.object(service.asyncio, 'wait_for', side_effect=short_wait):
            result = await service.analyze_distress(MESSAGE, transport=httpx.MockTransport(handler))
        self.assertEqual(result.provider, 'groq')

    def test_strict_schema(self):
        invalid = [dict(distress_score=x) for x in (-1, 101, True, 65.0, '65')]
        invalid += [dict(requires_attention='true'), dict(risk_level='HIGH'), dict(emotions='fear'),
                    dict(emotions=[5]), dict(emotions=[' ']), dict(emotions=['x'*33]),
                    dict(emotions=['fear']*9), dict(reason=' '), dict(reason='x'*401),
                    dict(provider='gemini'), dict(risk_level='low'), dict(requires_attention=False)]
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises((ValidationError, service.InvalidProviderResponse)):
                service.parse_indicators(json.dumps(dict(GOOD, **fields)))
        for raw in ('[]', '{}', 'null', '{"distress_score":65,"distress_score":65}', 'text ' + json.dumps(GOOD)):
            with self.assertRaises((ValidationError, ValueError, service.InvalidProviderResponse)):
                service.parse_indicators(raw)
        self.assertEqual(service.parse_indicators('```json\n'+json.dumps(GOOD)+'\n```').distress_score, 65)
        for score, risk in ((0,'low'),(24,'low'),(25,'medium'),(49,'medium'),(50,'high'),(74,'high'),(75,'critical'),(100,'critical')):
            result = service.parse_indicators(json.dumps(dict(GOOD, distress_score=score, risk_level=risk, requires_attention=score>=50)))
            self.assertEqual(result.distress_score, score)

    def test_key_not_in_config_repr(self):
        self.assertNotIn('test-secret', repr(service.provider_configs()))


class EndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import the actual full app and run real create_all on an isolated DB.
        # Production database.py and auth.py remain byte-for-byte unchanged.
        cls.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        with patch('sqlalchemy.create_engine', return_value=cls.engine):
            cls.main = importlib.import_module('app.main')
        from app.auth import create_access_token
        cls.headers = {'Authorization': 'Bearer ' + create_access_token({'user_id': 1, 'role': 'victim'})}

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(self.main.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_success_through_real_service_no_persistence(self):
        from app.database import Base
        from app.ai_service import analyze_distress
        async def mocked_http(message):
            return await analyze_distress(message, transport=httpx.MockTransport(reply))
        def counts():
            with self.engine.connect() as conn:
                return [conn.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables]
        before = counts()
        with patch('app.ai.analyze_distress', side_effect=mocked_http) as analyze:
            response = self.client.post('/api/ai/analyze', json={'message': MESSAGE}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), dict(GOOD, provider='gemini'))
        analyze.assert_awaited_once_with(MESSAGE)
        self.assertEqual(before, counts())

    def test_invalid_requests(self):
        with patch('app.ai.analyze_distress', new_callable=AsyncMock) as analyze:
            for payload in ({}, {'message':''}, {'message':' \t\n'}, {'message':'x'*4001},
                            {'message':5}, {'message':None}, {'message':'ok', 'extra':1}):
                self.assertEqual(self.client.post('/api/ai/analyze', json=payload, headers=self.headers).status_code, 422)
            analyze.assert_not_awaited()

    def test_controlled_503(self):
        async def all_fail(message):
            def fail(req):
                return httpx.Response(503, text=MESSAGE + 'test-secret-gemini')
            return await service.analyze_distress(message, transport=httpx.MockTransport(fail))
        with patch('app.ai.analyze_distress', side_effect=all_fail):
            response = self.client.post('/api/ai/analyze', json={'message':MESSAGE}, headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'detail':'AI analysis is temporarily unavailable.'})
        self.assertNotIn('test-secret', response.text)
        self.assertNotIn(MESSAGE, response.text)

    def test_protected_and_opt_in(self):
        with patch('app.ai.analyze_distress', new_callable=AsyncMock) as analyze:
            response = self.client.post('/api/ai/analyze', json={'message':MESSAGE})
            self.assertIn(response.status_code, (401,403))
            response = self.client.post('/api/ai/analyze', json={'message':MESSAGE}, headers={'Authorization':'Bearer invalid'})
            self.assertEqual(response.status_code, 401)
            with patch.dict(os.environ, {'AI_TEST_ENDPOINT_ENABLED':'false'}):
                response = self.client.post('/api/ai/analyze', json={'message':MESSAGE}, headers=self.headers)
                self.assertEqual(response.status_code,404)
            analyze.assert_not_awaited()

    def test_existing_routes(self):
        self.assertEqual(self.client.get('/').json(), {'message':'SIH backend is running'})
        self.assertEqual(self.client.get('/victim/test', headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/counsellor/test', headers=self.headers).status_code,403)
        self.assertEqual(self.client.get('/api/cases', headers=self.headers).status_code,403)
        self.assertEqual(self.client.get('/api/victim/dashboard', headers=self.headers).status_code,404)
        self.assertIn('/api/ai/analyze', self.client.get('/openapi.json').json()['paths'])

    def test_existing_password_hashing(self):
        from app.auth import pwd_context
        hashed = pwd_context.hash('synthetic-test-password')
        self.assertTrue(pwd_context.verify('synthetic-test-password', hashed))
        self.assertFalse(pwd_context.verify('wrong', hashed))


if __name__ == '__main__':
    unittest.main()
