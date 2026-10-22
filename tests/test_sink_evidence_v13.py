import pytest
from security_signature.sink_evidence_v12 import extract_sink_evidence as e12
from security_signature.sink_evidence_v13 import extract_sink_evidence as e13


def test_array_pointer_parameter_is_excluded_but_body_call_retained():
    code = 'int f(uint8_t (*map)[3]) { uint8_t(p); free(p); }'
    result = e13(code)
    assert [r['api_name'] for r in result['excluded_syntax']] == ['uint8_t']
    assert [r['expression'] for r in result['unknown_calls']] == ['uint8_t(p)']
    assert result['sink_apis'] == ['free']


def test_decorated_function_name_excluded_but_symbol_macro_in_body_unknown():
    result = e13('void RENAME(f)(int *x) { helper(RENAME(g)); }')
    assert [r['expression'] for r in result['excluded_syntax']] == ['RENAME(f)']
    assert 'RENAME(g)' in [r['expression'] for r in result['unknown_calls']]


@pytest.mark.parametrize('call,role', [
    ('fprintf(stderr, "%s", msg)', 'diagnostic_stderr'),
    ('fprintf(stdout, "%s", msg)', 'standard_stdout'),
    ('fprintf(file, "%s", msg)', 'stream_output_unresolved'),
    ('fprintf(stderr_alias, "%s", msg)', 'stream_output_unresolved'),
    ('printf("%s", msg)', 'standard_stdout'),
    ('snprintf(buf, size, "%s", msg)', 'buffer_formatting'),
    ('free(ptr)', 'not_assessed'),
])
def test_output_role_is_explicit_syntax_not_name_guess(call, role):
    code = 'void f() { '+call+'; }'
    before = e12(code)
    result = e13(code)
    assert result['recognized'][0]['output_role'] == role
    assert result['recognized'][0]['expression'] == before['recognized'][0]['expression']


def test_comments_do_not_define_function_body_or_stream_role():
    result = e13('/* { */ void RENAME(f)(void) { fprintf(/* x */ stderr, "x"); }')
    assert len(result['excluded_syntax']) == 1
    assert result['recognized'][0]['output_role'] == 'diagnostic_stderr'


def test_conditional_and_inactive_evidence_preserved():
    code = 'void f() {\n#if 0\nfree(p);\n#endif\n#ifdef F\nfprintf(stderr,"x");\n#endif\n}'
    old = e12(code)
    new = e13(code)
    assert new['recognized'][0]['preprocessor_state'] == 'conditional'
    assert new['inactive_calls'] == old['inactive_calls']
    assert old == e12(code)
