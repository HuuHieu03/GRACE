import hashlib
import json
from pathlib import Path

import pytest

from security_signature.sink_evidence import extract_sink_evidence as e1
from security_signature.sink_evidence_v11 import NEW_WRAPPER_RULES, extract_sink_evidence as e11


ROOT = Path(__file__).resolve().parent.parent
PROPOSALS = json.loads((ROOT/'project_docs/reports/sink_evidence_h1/wrapper_registry_proposals.json').read_text(encoding='utf-8'))
CASES = [(row['api_name'], row['proposed_families'][0]) for row in PROPOSALS]


@pytest.mark.parametrize('api,family', CASES)
def test_reviewed_rule_family_at_real_call_site(api, family):
    code = f'void sample(void) {{ {api}(x, nested(y)); }}'
    result = e11(code)
    assert result['sink_apis'] == [api]
    row = result['recognized'][0]
    assert row['family'] == family
    assert code[row['start']:row['end']] == f'{api}(x, nested(y))'
    assert row['semantic_validation'].startswith('caller_context_only')
    assert 'is_controlled' not in row


@pytest.mark.parametrize('api,family', CASES)
@pytest.mark.parametrize('template', [
    'void f(void) {{ /* {api}(x); */ }}',
    'void f(void) {{ char *s = "{api}(x);"; }}',
    'void f(void) {{ int {api}=0; {api}++; }}',
    'extern void {api}(void *x);',
    'void f(void) {{ extern void {api}(void *x); }}',
    'void {api}(void *x) {{ }}',
    '#define WRAPPER(x) {api}(x)\nvoid f(void) {{}}',
    'void f(void) {{ obj->{api}(x); }}',
    'void f(void) {{ obj.{api}(x); }}',
    'void f(void) {{ custom::{api}(x); }}',
    'void f(void) {{ {api}_unrelated(x); }}',
])
def test_wrapper_rules_do_not_promote_non_calls_or_lookalikes(api, family, template):
    result = e11(template.format(api=api))
    assert not result['recognized']


def test_rules_do_not_mutate_baseline_or_drop_other_unknowns():
    code = 'void f(void) { tcg_malloc(n); WRITEBGR24(x); free(p); obj->g_new(x); }'
    baseline = e1(code)
    result = e11(code)
    assert baseline == e1(code)
    assert set(result['sink_apis']) == {'tcg_malloc', 'free'}
    assert {r['api_name'] for r in result['unknown_calls']} == {'WRITEBGR24', 'g_new'}
    assert result['guard_assessment'] == 'not_performed'


def test_scope_matches_exact_approved_proposals_and_frozen_e1_source():
    assert dict(NEW_WRAPPER_RULES) == dict(CASES)
    summary = json.loads((ROOT/'project_docs/reports/sink_evidence_h1/summary.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT/'src/security_signature/sink_evidence.py').read_bytes()).hexdigest() == summary['E1_source_sha256']


def test_metadata_invariance_and_unbalanced_call_remains_diagnostic():
    code = 'void f(void) { openat(dirfd,path,flags); tcg_malloc('
    first = {'id': 'label_True.c', 'target': 1, 'func': code}
    second = {**first, 'id': 'label_False.c', 'target': 0}
    assert e11(first['func']) == e11(second['func'])
    assert e11(code)['sink_apis'] == ['openat']
    assert any(row['name'] == 'tcg_malloc' for row in e11(code)['diagnostics'])
