import hashlib

import pytest

from scripts.evaluate_sink_evidence_v11_fresh import build_annotations


def make_inputs():
    code='void f(void) { printf("live");\n#if 0\nprintf("disabled");\n#endif\n}'
    sha=hashlib.sha256(code.encode('utf-8')).hexdigest()
    packet=[{'opaque_id':f'E11-{i:03d}','code':code,'code_sha256':sha} for i in range(1,51)]
    manifest={'samples':[{'opaque_id':row['opaque_id'],'code_sha256':sha} for row in packet]}
    specs={'samples':[{'id':row['opaque_id'],'calls':[['printf','format_string',2]],
                       'exclude_occurrences':{'printf':[2]},'notes':'Second call lies in explicit #if 0.'}
                      for row in packet]}
    return packet,manifest,specs


def test_inactive_site_stays_explicit_and_is_not_silently_counted_positive():
    result=build_annotations(*make_inputs())
    assert len(result)==50
    for row in result:
        assert len(row['callsite_annotations'])==1
        assert row['callsite_annotations'][0]['expression']=='printf("live")'
        assert row['excluded_callsite_annotations'][0]['expression']=='printf("disabled")'
        assert row['excluded_callsite_annotations'][0]['exclusion_reason']=='explicit_if_zero_in_source_review'


def test_out_of_range_annotation_exclusion_fails():
    packet,manifest,specs=make_inputs()
    specs['samples'][0]['exclude_occurrences']['printf']=[3]
    with pytest.raises(ValueError,match='Invalid manually excluded'):
        build_annotations(packet,manifest,specs)


def test_changed_source_cannot_reuse_old_gold_spans():
    packet,manifest,specs=make_inputs()
    packet[0]['code']='/* source changed */'+packet[0]['code']
    with pytest.raises(ValueError,match='Frozen input changed'):
        build_annotations(packet,manifest,specs)


def test_duplicate_sample_cannot_replace_an_unreviewed_one():
    packet,manifest,specs=make_inputs()
    specs['samples'][1]=dict(specs['samples'][0])
    with pytest.raises(ValueError,match='50 uniquely matched'):
        build_annotations(packet,manifest,specs)
