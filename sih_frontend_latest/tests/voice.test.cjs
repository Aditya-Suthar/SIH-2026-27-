const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function harness(reply, token = 'victim-token') {
  const exports = {}; let request;
  const source = ts.transpileModule(fs.readFileSync('src/lib/voice.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  vm.runInNewContext(source, { exports, require: () => ({ API_BASE_URL: 'https://backend.example' }),
    localStorage: { getItem: () => token }, window: { location: { origin: 'https://frontend.example' } }, Error,
    fetch: async (url, options) => { request = { url, ...options }; if (reply instanceof Error) throw reply; return reply; } });
  return { transcribe: exports.transcribeVoice, request: () => request };
}
test('voice posts raw audio to the shared API with bearer auth and browser MIME', async () => {
  const h = harness({ ok: true, json: async () => ({ transcript: ' hello ', language: 'en' }) });
  const audio = new Blob(['audio'], { type: 'audio/webm;codecs=opus' });
  assert.equal((await h.transcribe(audio)).transcript, 'hello');
  const req = h.request();
  assert.equal(req.url, 'https://backend.example/api/victim/voice/transcribe');
  assert.equal(req.headers.Authorization, 'Bearer victim-token');
  assert.equal(req.headers['Content-Type'], audio.type);
  assert.equal(req.body, audio);
});
for (const status of [401, 403, 413, 415, 422, 503]) {
  test(`backend detail and HTTP ${status} are preserved`, async () => {
    const h = harness({ ok: false, status, json: async () => ({ detail: 'Backend reason' }) });
    await assert.rejects(h.transcribe(new Blob(['audio'])), new RegExp(`HTTP ${status}.*Backend reason`));
  });
}
test('HTML gateway failures retain HTTP status', async () => {
  const h = harness({ ok: false, status: 504, json: async () => { throw new Error('HTML'); } });
  await assert.rejects(h.transcribe(new Blob(['audio'])), /HTTP 504.*timed out/);
});
test('network failure reports URL and distinguishes unavailable HTTP status', async () => {
  const h = harness(new Error('Failed to fetch'));
  await assert.rejects(h.transcribe(new Blob(['audio'])), /https:\/\/backend.example.*No HTTP status.*https:\/\/frontend.example/);
});
test('missing token does not upload audio', async () => {
  const h = harness(null, null);
  await assert.rejects(h.transcribe(new Blob(['audio'])), /sign in/);
  assert.equal(h.request(), undefined);
});
