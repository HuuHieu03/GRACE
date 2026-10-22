import pytest

from security_signature.sink_evidence import extract_sink_evidence


@pytest.mark.parametrize('code', [
    'void f(void) { /* memcpy(d,s,n); */ }',
    'void f(void) { // free(p);\n }',
    'void f(void) { const char *s = "read(fd,b,n); memcpy(d,s,n)"; }',
    'void f(void) { int read = 0; read++; }',
    'extern void *malloc(size_t n);',
    'typedef void *handle; handle malloc(size_t);',
    'void f(void) { extern void free(void *p); }',
    'void free(void *p) { }',
    '#define COPY(x,y,n) memcpy(x,y,n)\nvoid f(void) {}',
    '#define COPY(x,y,n) \\\n+ memcpy(x,y,n)\nvoid f(void) {}',
])
def test_non_calls_do_not_create_sinks(code):
    assert extract_sink_evidence(code)['recognized'] == []


def test_nested_calls_spans_and_repeated_calls():
    code = 'void f(void) {\n memcpy(d, malloc(n), n); free(d); free(p); }'
    result = extract_sink_evidence(code)
    assert [r['api_name'] for r in result['recognized']] == ['memcpy','malloc','free','free']
    for row in result['recognized']:
        assert code[row['start']:row['end']] == row['expression']
        assert row['line'] == 2
    assert result['recognized'][0]['expression'] == 'memcpy(d, malloc(n), n)'


@pytest.mark.parametrize('statement', ['return malloc(n);', 'p = malloc(n);',
                                      'if (ok) free(p);', '(void)memcpy(d,s,n);',
                                      'for (i=0;i<n;i++) free(p);'])
def test_expression_contexts(statement):
    assert extract_sink_evidence('void f(void) {'+statement+'}')['recognized']


def test_wrapper_exact_name_and_unknown_helper_macro_member():
    code = 'void f(void) { bdrv_pread(bs,o,b,n); bdrv_mystery(bs); WRITEBGR24(x); obj->free(p); }'
    result = extract_sink_evidence(code)
    assert result['sink_apis'] == ['bdrv_pread']
    assert result['recognized'][0]['family'] == 'block_read'
    assert {r['api_name'] for r in result['unknown_calls']} == {'bdrv_mystery','WRITEBGR24','free'}


@pytest.mark.parametrize('code', [
    'void f(void) { if (n > max) log_error(); memcpy(d,s,n); }',
    'void f(void) { memcpy(d,s,n); if (n > max) return; }',
    'void f(void) { if (other < max) memcpy(d,s,n); }',
])
def test_guard_presence_does_not_claim_control(code):
    result = extract_sink_evidence(code)
    assert 'memcpy' in result['sink_apis']
    assert result['guard_assessment'] == 'not_performed'
    assert all('is_controlled' not in r for r in result['recognized'])


def test_escaped_strings_and_comment_delimiters():
    code = r'void f(void) { char *s = "escaped \" // free(p)"; memcpy(d,s,n); }'
    assert extract_sink_evidence(code)['sink_apis'] == ['memcpy']


def test_preprocessor_does_not_eat_next_executable_line():
    code = '#include <string.h>\nvoid f(void) { memcpy(d,s,n); }'
    assert extract_sink_evidence(code)['sink_apis'] == ['memcpy']


def test_truncated_expression_is_unknown_not_complete_evidence():
    result = extract_sink_evidence('void f(void) { memcpy(d,s,')
    assert result['recognized'] == []
    assert any(r['name']=='memcpy' for r in result['diagnostics'])


def test_code_only_interface_ignores_external_target_metadata():
    first={'id':'id_1_label_True.c','target':1,'func':'void f(void) { av_mallocz(n); }'}
    second={**first,'id':'id_900_label_False.c','target':0}
    assert extract_sink_evidence(first['func']) == extract_sink_evidence(second['func'])


def test_member_named_api_is_not_assumed_library_function():
    result=extract_sink_evidence('void f(void) { p->read(b); p.free(b); custom::free(b); }')
    assert result['recognized'] == []
    assert len(result['unknown_calls']) == 3
