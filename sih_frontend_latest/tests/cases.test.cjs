const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

function load(file, overrides = {}) {
  const exports = {};
  const source = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  }}).outputText;
  vm.runInNewContext(source, { exports, require: name => {
    if (Object.hasOwn(overrides, name)) return overrides[name];
    if (!name.startsWith('.')) return require(name);
    const target = path.resolve(path.dirname(file), name);
    return load(['.ts', '.tsx'].map(ext => target + ext).find(fs.existsSync), overrides);
  }, AbortController });
  return exports;
}

const { filterCases, matchesCaseSearch, victimDisplayName } = load('src/lib/caseIdentity.ts');
const cases = [
  { caseId: 'SAH-A6D3AA80338A', victimName: 'Aditya Suthar', assignedCounsellor: 'Counsellor Four', riskLevel: 'Critical', interventionStatus: 'Follow-up pending', lastAssessment: '2026-09-12T17:55:00Z' },
  { caseId: 'SAH-SECOND', victimName: 'Another Person', assignedCounsellor: 'Counsellor Two', riskLevel: 'Low', interventionStatus: 'Monitoring' },
];

test('case search matches victim name and ID, ignoring case and surrounding whitespace', () => {
  for (const search of ['Aditya', ' sUtHaR ', 'SAH-A6D3AA80338A', 'a6d3aa']) {
    const found = filterCases(cases, search, 'All', 'All');
    assert.equal(found.length, 1);
    assert.equal(found[0].caseId, cases[0].caseId);
  }
  assert.equal(filterCases(cases, 'absent', 'All', 'All').length, 0);
});

test('name search preserves counsellor search, combined filters and incoming order', () => {
  assert.equal(filterCases(cases, 'Counsellor Four', 'Critical', 'Follow-up pending')[0], cases[0]);
  assert.equal(filterCases(cases, 'Aditya', 'Low', 'All').length, 0);
  assert.equal(filterCases(cases, 'Aditya', 'Critical', 'Monitoring').length, 0);
  assert.deepEqual(Array.from(filterCases(cases, ' ', 'All', 'All')), cases);
  assert.equal(matchesCaseSearch(cases[0], 'Aditya'), true);
});

test('missing and blank names display a safe fallback and remain searchable by ID', () => {
  for (const name of [undefined, null, '', '   ']) {
    assert.equal(victimDisplayName(name), 'Unnamed Victim');
    assert.equal(matchesCaseSearch({ caseId: 'SAH-LEGACY', victimName: name }, 'legacy'), true);
  }
  assert.equal(victimDisplayName('  Name  '), 'Name');
});

test('duplicate names keep distinct case identities', () => {
  const rows = [cases[0], { ...cases[0], caseId: 'SAH-DUPLICATE' }];
  assert.equal(filterCases(rows, 'Aditya', 'All', 'All').length, 2);
  assert.equal(filterCases(rows, 'SAH-DUPLICATE', 'All', 'All')[0].caseId, 'SAH-DUPLICATE');
});

test('shared identity renders name first, muted smaller ID, fallback and escaped text', () => {
  const { CaseIdentity } = load('src/components/CaseIdentity.tsx');
  const html = renderToStaticMarkup(React.createElement(CaseIdentity, { caseId: 'SAH-1', victimName: '<script>name</script>' }));
  assert.ok(html.indexOf('&lt;script&gt;name') < html.indexOf('SAH-1'));
  assert.match(html, /font-medium text-foreground/);
  assert.match(html, /text-xs font-normal text-muted-foreground/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(renderToStaticMarkup(React.createElement(CaseIdentity, { caseId: 'SAH-2' })), /Unnamed Victim/);
});

test('case API client retains the response name and existing fields and encodes detail IDs', async () => {
  const requests = [];
  const { getCases, getCase } = load('src/lib/cases.ts', { './api': { api: async (url, options) => {
    requests.push({ url, options }); return url === '/api/cases' ? cases : cases[0];
  }}});
  const signal = new AbortController().signal;
  assert.equal((await getCases(signal))[0].victimName, 'Aditya Suthar');
  assert.equal((await getCase('SAH/A', signal)).caseId, cases[0].caseId);
  assert.equal(requests[0].url, '/api/cases');
  assert.equal(requests[0].options.signal, signal);
  assert.equal(requests[1].url, '/api/cases/SAH%2FA');
});

test('Cases table renders the searched person with existing fields and View control', () => {
  let index = 0;
  const states = [cases, false, '', 'Aditya', 'Critical', 'Follow-up pending'];
  const native = tag => ({ children }) => React.createElement(tag, null, children);
  const { default: Cases } = load('src/pages/Cases.tsx', {
    react: { ...React, useState: () => [states[index++], () => {}], useEffect: () => {}, useMemo: fn => fn() },
    'react-router-dom': { useNavigate: () => () => {} },
    '../components/ui/card': { Card: native('section'), CardContent: native('div'), CardHeader: native('header'), CardTitle: native('h2') },
    '../components/ui/badge': { Badge: native('span') },
    '../components/ui/button': { Button: native('button') },
    '../lib/cases': { getCases: async () => cases },
  });
  const html = renderToStaticMarkup(React.createElement(Cases));
  for (const value of ['Aditya Suthar', 'SAH-A6D3AA80338A', 'Counsellor Four', '2026-09-12T17:55:00Z', 'Follow-up pending', '>View<']) {
    assert.ok(html.includes(value), value);
  }
  assert.doesNotMatch(html, /Another Person/);
  assert.match(html, /Showing 1 of 2 total cases/);
});
