"""Synthetic policy tests, not experimental retrieval results."""
import numpy as np
import pytest
from scripts.run_retrieval_h2 import project, features, active, choose, score, validate_vectors, compare


def test_labels_and_filenames_do_not_change_ranking_inputs():
    a = dict(func='void f(){ memcpy(a,b,n); }', nodes=[{'type': 'CALL', 'filename': 'unsafe_1.c'}],
             edges=[], target=1, id='vulnerable_1.c')
    b = {**a, 'target': 0, 'id': 'safe_0.c', 'nodes': [{'type': 'CALL', 'filename': 'safe_0.c'}]}
    pa, pb = project([a], 'Q')[0], project([b], 'Q')[0]
    assert pa == pb
    assert score(pa, pb, features(pa), features(pb)) == score(pb, pa, features(pb), features(pa))


def test_conditional_only_cannot_force_family_match():
    row = project([{'func': 'void f(){\n#if FLAG\n memcpy(a,b,n);\n#endif\n}'}], 'Q')[0]
    evidence, _ = features(row)
    assert evidence['recognized']
    assert not active(evidence, 'family')
    ranked = [{'id': 'T-1', 'active_families': []}, {'id': 'T-2', 'active_families': ['buffer_copy']}]
    assert choose(ranked, set()) == ('T-1', 'T-1', 'query_has_no_active_family', 0)


def test_r1_preserves_r0_order_within_shared_pool():
    ranked = [{'id': 'T-1', 'active_families': []},
              {'id': 'T-2', 'active_families': ['copy']},
              {'id': 'T-3', 'active_families': ['copy']}]
    assert choose(ranked, {'copy'}) == ('T-1', 'T-2', 'same_active_family', 2)
    assert choose(ranked, {'free'}) == ('T-1', 'T-1', 'no_matching_candidate', 0)
    with pytest.raises(ValueError):
        choose([], {'copy'})


@pytest.mark.parametrize('vectors', [np.zeros((2, 256), dtype='float32'),
                                    np.zeros((2, 768), dtype='float64'),
                                    np.full((2, 768), np.nan, dtype='float32')])
def test_invalid_embeddings_fail_closed(vectors):
    with pytest.raises(ValueError):
        validate_vectors(vectors, 2)


def test_shared_top50_excludes_outside_candidate_and_resolves_ties_stably():
    # Synthetic vectors exercise policy mechanics only; never research data.
    train = project([{'func': 'void f(){ free(p); }'} for _ in range(51)], 'T')
    train[-1]['func'] = 'void f(){ memcpy(a,b,n); }'
    queries = project([{'func': 'void f(){ memcpy(a,b,n); }'}], 'Q')
    vectors = np.zeros((51, 768), dtype='float32')
    vectors[-1] = 10
    records, summary = compare(train, queries, vectors, np.zeros((1, 768), dtype='float32'))
    record = records[0]
    assert len(record['shared_pool']) == 50
    assert record['r0_order'] == [r['id'] for r in train[:50]]
    assert record['reason'] == 'no_matching_candidate'
    assert record['r0'] == record['r1'] == train[0]['id']
    assert summary['fallback'] == 1
