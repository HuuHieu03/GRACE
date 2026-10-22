"""Validate real relevance sheets; never infer missing reviewer decisions."""
import csv
import json
from pathlib import Path
from collections import Counter
from scripts.run_retrieval_h2 import write_json

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT/'project_docs/reports/retrieval_h2/followup_2026-10-22'
CHOICES = {
    'operation_alignment': {'same', 'related', 'different', 'insufficient'},
    'object_role_alignment': {'same', 'partial', 'different', 'insufficient'},
    'guard_comparability': {'comparable', 'different', 'not_applicable', 'insufficient'},
    'overall_relevance': {'relevant', 'partial', 'irrelevant', 'insufficient'}}


def analyze(packet, sheets):
    expected = {r['review_id'] for r in packet}
    reports, ratings = {}, {}
    for name, rows in sheets.items():
        ids = [r['review_id'] for r in rows]
        if len(ids) != len(set(ids)) or set(ids) != expected:
            raise ValueError(name + ': duplicate, missing or unexpected review IDs')
        complete = {}
        for row in rows:
            for field, choices in CHOICES.items():
                if row[field] and row[field] not in choices:
                    raise ValueError(name + ': invalid '+field+' at '+row['review_id'])
            if all(row[f] for f in CHOICES) and row['query_evidence'].strip() and row['demo_evidence'].strip():
                complete[row['review_id']] = row['overall_relevance']
        ratings[name] = complete
        reports[name] = dict(rows=len(rows), complete=len(complete), incomplete=len(rows)-len(complete))
    result = dict(sheets=reports, independence='not verified by file validation',
                  agreement=None, cohens_kappa=None, status='PENDING_COMPLETE_REVIEWS', discordant=[])
    if all(len(r) == len(expected) for r in ratings.values()):
        a, b = ratings['A'], ratings['B']
        observed = sum(a[k] == b[k] for k in expected)/len(expected)
        ca, cb = Counter(a.values()), Counter(b.values())
        chance = sum(ca[c]*cb[c] for c in CHOICES['overall_relevance'])/len(expected)**2
        result.update(status='COMPLETE_SHEETS_INDEPENDENCE_NOT_VERIFIED', agreement=observed,
                      cohens_kappa=(observed-chance)/(1-chance) if chance < 1 else None,
                      kappa_undefined=chance == 1, marginal_counts={'A':dict(ca), 'B':dict(cb)},
                      discordant=[dict(review_id=k, A=a[k], B=b[k]) for k in sorted(expected) if a[k] != b[k]])
    return result


def main():
    packet = json.loads((FOLDER/'relevance_review_packet.json').read_text(encoding='utf-8'))
    sheets = {}
    for name in ['A', 'B']:
        with (FOLDER/f'relevance_sheet_reviewer_{name}.csv').open(encoding='utf-8-sig', newline='') as handle:
            sheets[name] = list(csv.DictReader(handle))
    result = analyze(packet, sheets)
    write_json(FOLDER/'review_completion_status.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
