import pytest
from scripts.check_h2_relevance_reviews import analyze


def sheet(labels):
    return [dict(review_id=str(i), operation_alignment='same', object_role_alignment='same',
                 guard_comparability='insufficient', overall_relevance=label,
                 query_evidence='query snippet', demo_evidence='demo snippet') for i, label in enumerate(labels)]


def test_missing_ballots_do_not_create_kappa():
    a = sheet(['relevant', ''])
    result = analyze([{'review_id': '0'}, {'review_id': '1'}], {'A': a, 'B': a})
    assert result['cohens_kappa'] is None and result['agreement'] is None
    assert result['status'] == 'PENDING_COMPLETE_REVIEWS'


def test_balanced_half_agreement_has_zero_kappa():
    packet = [{'review_id': str(i)} for i in range(4)]
    result = analyze(packet, {'A': sheet(['relevant','relevant','irrelevant','irrelevant']),
                              'B': sheet(['relevant','irrelevant','relevant','irrelevant'])})
    assert result['agreement'] == .5 and result['cohens_kappa'] == 0
    assert len(result['discordant']) == 2


def test_same_single_category_kappa_is_undefined():
    result = analyze([{'review_id':'0'}], {'A':sheet(['relevant']), 'B':sheet(['relevant'])})
    assert result['agreement'] == 1 and result['kappa_undefined']
    assert result['cohens_kappa'] is None


def test_duplicate_ids_fail():
    with pytest.raises(ValueError):
        analyze([{'review_id':'0'}], {'A':sheet(['relevant'])*2,'B':sheet(['relevant'])})
