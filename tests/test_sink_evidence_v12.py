import pytest

from security_signature.sink_evidence_v11 import extract_sink_evidence as e11
from security_signature.sink_evidence_v12 import evaluate_condition, extract_sink_evidence as e12


@pytest.mark.parametrize('condition,expected',[
    ('0',False),('1',True),('(0)',False),('!0',True),('!1',False),
    ('0U',False),('0x0UL',False),('010',True),('0b0',False),
    ('FLAG',None),('defined(FLAG)',None),('defined FLAG',None),
    ('0 && FLAG',False),('FLAG && 0',False),('FLAG || 1',True),
    ('FLAG || 0',None),('!defined(FLAG)',None),
    ('(1 && (0 || 1))',True),('0 == 1',None),('1 + 0',None),
    ('0 &&',None),('',None),('defined()',None),('08',None),
])
def test_only_provable_conditions_are_evaluated(condition,expected):
    assert evaluate_condition(condition) is expected


def test_if_zero_removed_else_kept_and_offsets_preserved():
    code='void f(void) {\r\n#if 0\r\nfree(dead);\r\n#else\r\nmemcpy(d,s,n);\r\n#endif\r\n}'
    result=e12(code)
    assert result['sink_apis']==['memcpy']
    row=result['recognized'][0]
    assert row['preprocessor_state']=='active'
    assert code[row['start']:row['end']]=='memcpy(d,s,n)'
    assert row['line']==5
    assert result['inactive_calls'][0]['expression']=='free(dead)'


def test_nested_dead_parent_dominates_unknown_child_and_active_sibling():
    code='void f(void) {\n#if 0\n#ifdef FOO\nfree(a);\n#else\nfree(b);\n#endif\n#endif\nfree(c);\n}'
    result=e12(code)
    assert [row['expression'] for row in result['recognized']]==['free(c)']
    assert len(result['inactive_calls'])==2


def test_unknown_build_both_branches_remain_conditional():
    code='void f(void) {\n#ifdef FEATURE\nfree(a);\n#else\nmemcpy(d,s,n);\n#endif\n}'
    result=e12(code)
    assert set(result['sink_apis'])=={'free','memcpy'}
    assert result['unconditional_sink_apis']==[]
    assert all(row['preprocessor_state']=='conditional' for row in result['recognized'])
    assert result['inactive_calls']==[]


def test_elif_chain_and_else_after_guaranteed_branch():
    code='void f(void) {\n#if FLAG\nfree(a);\n#elif 0\nfree(b);\n#elif 1\nfree(c);\n#else\nfree(d);\n#endif\n}'
    result=e12(code)
    assert [row['expression'] for row in result['recognized']]==['free(a)','free(c)']
    assert all(row['preprocessor_state']=='conditional' for row in result['recognized'])
    assert {row['expression'] for row in result['inactive_calls']}=={'free(b)','free(d)'}


def test_first_true_branch_suppresses_later_elif_and_else():
    code='void f(void) {\n#if 1\nfree(a);\n#elif FEATURE\nfree(b);\n#else\nfree(c);\n#endif\n}'
    assert [row['expression'] for row in e12(code)['recognized']]==['free(a)']


def test_comments_literals_and_define_body_do_not_change_branch_state():
    code='void f(void) { /*\n#if 0\n*/\nchar *s="#if 0";\n#define FAKE(x) free(x)\nfree(p);\n}'
    result=e12(code)
    assert [row['expression'] for row in result['recognized']]==['free(p)']
    assert result['recognized'][0]['preprocessor_state']=='active'


def test_multiline_constant_false_condition():
    code='void f(void) {\n#if 0 \\\n && FLAG\nfree(p);\n#endif\nfree(q);\n}'
    assert [row['expression'] for row in e12(code)['recognized']]==['free(q)']


def test_unknown_arithmetic_is_not_assumed_false():
    code='void f(void) {\n#if SIZE > 4\nfree(p);\n#endif\n}'
    result=e12(code)
    assert result['recognized'][0]['preprocessor_state']=='conditional'


def test_dead_malformed_code_cannot_poison_active_bracket_matching():
    code='void f(void) {\n#if 0\nnot_c( (((\n#endif\nmemcpy(d,s,n);\n}'
    assert [row['expression'] for row in e12(code)['recognized']]==['memcpy(d,s,n)']


def test_unclosed_conditional_is_diagnostic_and_not_certainly_dead():
    code='void f(void) {\n#if 0\nfree(p);'
    result=e12(code)
    assert result['recognized'][0]['preprocessor_state']=='conditional'
    assert any(row['reason']=='unclosed_conditional' for row in result['preprocessor_diagnostics'])


@pytest.mark.parametrize('directive',['#else','#elif 1','#endif'])
def test_orphan_directive_reports_diagnostic(directive):
    result=e12('void f(void) {\n'+directive+'\nfree(p);\n}')
    assert result['preprocessor_diagnostics']
    assert result['recognized']


def test_unknown_calls_are_conditioned_and_old_version_does_not_change():
    code='void f(void) {\n#if 0\nWRITEBGR24(x);\n#endif\n#ifdef FEATURE\nhelper(x);\n#endif\n}'
    old=e11(code)
    result=e12(code)
    assert old==e11(code)
    assert [row['api_name'] for row in result['unknown_calls']]==['helper']
    assert result['unknown_calls'][0]['preprocessor_state']=='conditional'
    assert result['inactive_calls'][0]['api_name']=='WRITEBGR24'


def test_call_arguments_crossing_unknown_branch_are_marked_conditional():
    code='void f(void) { free(\n#ifdef FEATURE\np\n#else\nq\n#endif\n); }'
    result=e12(code)
    assert result['recognized'][0]['preprocessor_state']=='conditional'
    assert result['recognized'][0]['expression']==code[code.index('free('):code.index(';')]


@pytest.mark.parametrize('tail',['#else','#elif 1'])
def test_malformed_branches_after_else_are_not_treated_as_certainly_inactive(tail):
    code='void f(void) {\n#if 1\nfree(p);\n#else\nfree(q);\n'+tail+'\nfree(r);\n#endif\n}'
    result=e12(code)
    assert result['preprocessor_diagnostics']
    assert any(row['expression']=='free(r)' and row['preprocessor_state']=='conditional' for row in result['recognized'])
