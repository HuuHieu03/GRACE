import pytest

from scripts.evaluate_sink_evidence_annotations import locate_reviewed_calls


def test_annotation_span_resolves_nested_arguments_and_parentheses_in_literals():
    code='void f(void) { log("unbalanced ) (", nested(x, y)); }'
    spans=locate_reviewed_calls(code,'log',1)
    assert len(spans)==1
    start,end=spans[0]
    assert code[start:end]=='log("unbalanced ) (", nested(x, y))'


def test_annotation_span_handles_multiline_comments_and_repeated_sites():
    code='void f(void) { copy(d, /* ) */ s,\n n); copy(x,y,m); }'
    spans=locate_reviewed_calls(code,'copy',2)
    assert [code[start:end] for start,end in spans]==['copy(d, /* ) */ s,\n n)','copy(x,y,m)']


def test_annotation_count_drift_cannot_silently_change_ground_truth():
    with pytest.raises(ValueError,match='reviewed count'):
        locate_reviewed_calls('void f(void) { free(a); free(b); }','free',1)


def test_incomplete_reviewed_call_is_rejected_instead_of_scored_as_complete():
    with pytest.raises(ValueError,match='unclosed annotated expression'):
        locate_reviewed_calls('void f(void) { memcpy(d,s,','memcpy',1)
