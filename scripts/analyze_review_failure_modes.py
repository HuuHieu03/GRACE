"""Analyze user-confirmed adjudication; preserve original votes and kappa.

The taxonomy is an explicit qualitative annotation, not a model prediction.
Run after finalize_blind_review_adjudication.py. No API/GPU/network required.
"""
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / 'project_docs/reports'
CHOICE = 'better_demo (A/B/Equal/Neither)'

MECHANISMS = {
    1:'physical_memory_read', 3:'reference_lifetime_during_recursive_drain',
    4:'pixel_dimension_alignment', 5:'sector_range_validation', 6:'timer_notification',
    7:'stub_without_executed_sink', 9:'library_load_allocation_cleanup',
    10:'heap_and_file_cleanup', 12:'device_tree_property_update',
    13:'pixel_SIMD_load_store', 14:'MMIO_offset_dispatch',
    15:'stream_creation_after_index_check', 19:'bounded_page_update_append',
    20:'SCSI_request_lifetime', 23:'count_overflow_before_allocation_read',
    24:'integer_shift_width', 25:'callback_buffer_contract',
    26:'masked_register_write_DMA_IRQ', 28:'audio_channel_layout_parity',
    29:'signed_integer_subtraction', 31:'seek_callback_and_fallback',
    36:'H264_parameter_set_validation', 39:'SIMD_color_conversion_store',
    40:'HEVC_decode_and_frame_lifetime', 43:'pixel_kernel_padding_stride',
    45:'port_IO_request_count_size', 46:'pixel_kernel_stride_pointer_step',
    47:'path_xattr_errno_cleanup', 48:'opcode_table_registration',
    50:'TTA_Rice_filter_channel_index',
}
GUARD_ROLE = {5,12,19,24,28}
NO_REFERENCE = {7,29}
CONTEXT_LIMIT = {7,13,25,26,28,36,39,43,46,50}
ROLE_REASONS = {
    'OPERATION_MISMATCH': 'Demo không tái hiện đủ cụ thể thao tác/dòng dữ liệu của target; cùng domain, token hoặc pointer operation chưa đủ.',
    'GUARD_ROLE_MISMATCH': 'Điểm phân biệt chính là vai trò biến hoặc guard: miền sector, kết quả lookup, giới hạn append, shift width hoặc parity; demo thiếu quan hệ tương ứng.',
    'NO_MATCHING_REFERENCE_FOR_SMALL_TARGET': 'Target là stub hoặc phép toán tối giản; không có demo minh họa cùng thao tác/tiền điều kiện để lựa chọn.',
}


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def save_csv(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_paths = {name: REPORTS/f'blind_review_sheet_{name}.csv' for name in ['hieu','dung']}
    hashes = {name: sha(path) for name, path in source_paths.items()}
    tf, technical = load_csv(REPORTS/'blind_review_technical_review_50.csv')
    _, hieu = load_csv(source_paths['hieu'])
    hm = {int(r['sample_idx']):r for r in hieu}
    keys = json.loads((REPORTS/'blind_review_answer_key.json').read_text(encoding='utf-8'))['answer_key']
    km = {int(r['sample_idx']):r for r in keys}
    confirmed = []
    for row in technical:
        record = dict(row)
        record['acceptance_status'] = 'USER_CONFIRMED_ADJUDICATION'
        record['accepted_on'] = '2026-10-21'
        record['acceptance_basis'] = 'User confirmed adjudication decisions in conversation; no additional independent rater votes inferred'
        confirmed.append(record)
    save_csv(REPORTS/'blind_review_confirmed_adjudication_50.csv', list(confirmed[0]), confirmed)
    af, adjudication = load_csv(REPORTS/'blind_review_adjudication.csv')
    for row in adjudication:
        row['consensus_choice'] = row['technical_choice']
        row['consensus_evidence'] = row['technical_evidence']
        row['acceptance_status'] = 'USER_CONFIRMED_ADJUDICATION'
        row['accepted_by'] = 'User confirmation in conversation; not two newly recorded independent votes'
    save_csv(REPORTS/'blind_review_adjudication.csv', af+[f for f in ['acceptance_status','accepted_by'] if f not in af], adjudication)

    failures = []
    for row in confirmed:
        if row['technical_choice'] != 'Neither':
            continue
        idx = int(row['sample_idx'])
        category = 'GUARD_ROLE_MISMATCH' if idx in GUARD_ROLE else ('NO_MATCHING_REFERENCE_FOR_SMALL_TARGET' if idx in NO_REFERENCE else 'OPERATION_MISMATCH')
        source, key = hm[idx], km[idx]
        failures.append({
            'sample_idx':idx, 'target_id':row['target_id'],
            'target_mechanism':MECHANISMS[idx], 'primary_failure_mode':category,
            'classification_reason':ROLE_REASONS[category],
            'secondary_context_limit':idx in CONTEXT_LIMIT,
            'baseline_demo_id':key['baseline_demo_id'],
            'security_aware_demo_id':key['security_aware_demo_id'],
            'same_demo_id':key['baseline_demo_id']==key['security_aware_demo_id'],
            'target_code':source['target_code_snippet'], 'demo_A_code':source['demo_A_snippet'],
            'demo_B_code':source['demo_B_snippet'], 'code_evidence':row['technical_evidence'],
            'pipeline_stage_attribution':'UNKNOWN: complete shared candidate ranking not archived',
        })
    assert len(failures)==30 and {r['sample_idx'] for r in failures}==set(MECHANISMS)
    save_csv(REPORTS/'retrieval_failure_modes_neither_30.csv', list(failures[0]), failures)

    # Corroborate selection provenance with the cached pairs, not just labels.
    b3=json.loads((ROOT/'output/stage3/b3_vs_b2_comparison_report.json').read_text(encoding='utf-8'))
    b3m={r['target_id']:r for r in b3['detailed_records_b3']}
    label_selected_matches = 0
    for key in keys:
        pair=b3m[key['target_id']]['contrastive_pair']
        selected=pair['vulnerable' if int(key['target_label'])==1 else 'safe']
        label_selected_matches += selected.get('id')==key['security_aware_demo_id']
    category_counts=Counter(r['primary_failure_mode'] for r in failures)
    summary={
        'date':'2026-10-21', 'acceptance':'User-confirmed technical adjudication',
        'original_sheet_hashes':hashes, 'original_kappa':0.3151, 'original_agreement_pct':48.0,
        'reviewed_samples':50, 'neither_count':30, 'neither_pct':60.0,
        'primary_failure_counts':dict(category_counts),
        'secondary_context_limit_count':sum(r['secondary_context_limit'] for r in failures),
        'taxonomy_basis':'Explicit qualitative annotation of confirmed judgments; not an independent benchmark',
        'review_selection_provenance':{
            'security_demo_label_equals_target':sum(k['security_aware_demo_label']==k['target_label'] for k in keys),
            'security_demo_matches_target_label_selected_B3_pair_member':label_selected_matches,
            'checked_samples':len(keys),
            'source':'scripts/generate_blind_review_sheets.py::load_retrieval_demonstrations',
            'finding':'Security-aware review arm is a target-label-selected B3 pair member, not an independently cached security top-1 ranking',
            'scope':'Review sheet construction; does not establish that inference retrieval used target labels',
        },
        'reuse_statistics':{},
        'candidate_stage_diagnosis':'Cannot distinguish candidate recall failure from reranker failure from selected demos alone',
        'next_experiment':'Label-independent top-1 security reranker versus same-top-50 reranker with same-sink-family preference; candidate evidence audit first',
    }
    for method in ['baseline','security_aware']:
        counts=Counter(k[f'{method}_demo_id'] for k in keys)
        summary['reuse_statistics'][method]={'unique_demos':len(counts),'top_demo_count':counts.most_common(1)[0][1],
            'top_three_count':sum(n for _,n in counts.most_common(3)), 'top_five':counts.most_common(5)}
    assert label_selected_matches==50
    # Diagnostic only: do not change the production extractor or its scores.
    sys.path.insert(0, str(ROOT/'src'))
    from security_signature.extractor import extract_security_signature
    split=json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))
    targets={str(r['id']):r for r in split['sample_details']}
    noncode=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    diagnostics=[]
    for row in failures:
        target=targets[row['target_id']]
        code=target['func']
        raw=extract_security_signature(code)
        graph=extract_security_signature(code, target.get('nodes',[]), target.get('edges',[]))
        cleaned=extract_security_signature(noncode.sub(' ',code))
        diagnostics.append({'sample_idx':row['sample_idx'],'target_id':row['target_id'],
                            'code_only_sink_apis':';'.join(sorted(raw.sink_apis)),
                            'code_plus_graph_sink_apis':';'.join(sorted(graph.sink_apis)),
                            'code_without_comments_literals_sink_apis':';'.join(sorted(cleaned.sink_apis)),
                            'text_tokens_removed_from_sink_apis':';'.join(sorted(raw.sink_apis-cleaned.sink_apis)),
                            'note':'Diagnostic call of current extractor; empty APIs are not proof of no dangerous operation'})
    save_csv(REPORTS/'retrieval_sink_evidence_diagnostic_30.csv',list(diagnostics[0]),diagnostics)
    summary['sink_evidence_diagnostic']={
        'code_only_empty':sum(not r['code_only_sink_apis'] for r in diagnostics),
        'code_plus_graph_empty':sum(not r['code_plus_graph_sink_apis'] for r in diagnostics),
        'cleaned_text_empty':sum(not r['code_without_comments_literals_sink_apis'] for r in diagnostics),
        'samples_with_noncode_token_sink_evidence':sum(bool(r['text_tokens_removed_from_sink_apis']) for r in diagnostics),
        'scope':'30 Neither targets only; token stripping is diagnostic, not a C parser or a validated extractor replacement',
    }
    assert {name:sha(path) for name,path in source_paths.items()}==hashes
    (REPORTS/'retrieval_failure_modes_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
