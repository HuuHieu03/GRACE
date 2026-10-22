"""Build a technical adjudication packet without changing either rater's votes.

Decisions below are explicit code-review judgments, not generated human votes.
Run from any directory. No LLM/API calls and no use of retrieval scores.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / 'project_docs/reports'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Revised decisions apply to all 50 cases, including originally agreed cases.
# Other judgments retain the Hiếu submission as the review starting point,
# with their existing evidence explicitly carried into the technical record.
REVISIONS = {
    6: ('Neither', 'NNNNNN', 'timerlist_notify và queue callback chỉ cùng dispatch. Không có cùng thao tác hay guard clock/queue; error_report của B cũng không phù hợp.'),
    12: ('Neither', 'NNNNNN', 'fdt_path_offset -> fdt_setprop khác permission-check -> block attach. Chỉ cùng if(ret < 0) không đủ để chọn A.'),
    13: ('Neither', 'PPUNNU', 'Target movq đọc/ghi pixel thật; A gen_store sinh mã guest store. Cùng chữ store/address chưa chứng minh cùng cơ chế bộ đệm hoặc guard stride; B rỗng.'),
    14: ('Neither', 'PPPNPN', 'Target dispatch MMIO offset và đọc bảng ID; A acknowledge IRQ rồi kiểm tra sentinel 1023. Cùng thiết bị/báo lỗi chưa đủ; B TPM read-size cũng khác vai trò.'),
    15: ('Neither', 'NNNNNN', 'Target kiểm tra nb_output_files trước output_files[index] và tạo stream. A permission-check/attach, B socket-kind dispatch không minh họa cùng count/index guard.'),
    16: ('B', 'PPPPPP', 'B đọc metadata extension/header và kiểm tra ext.len trước đọc/ghi backing_format; gần target parser metadata audio hơn A giải mã delta vào frame. Chỉ khớp một phần, không tái hiện arithmetic channels/sample_rate.'),
    19: ('Neither', 'PPPNNN', 'Target chặn append ram_pages_to_update[index++] khi đầy; A reset size_stat theo threshold, không bảo vệ append cùng vai trò. B rỗng.'),
    26: ('Neither', 'PPNPPN', 'Đã đọc hết cs_write và qcow_read_extensions. Target chọn thanh ghi bằng mask 0x0f/0x1f, ghi dregs[iaddr] và điều khiển DMA/IRQ; A guard ext.len trước đọc chuỗi backing_format, B size-check phản hồi TPM. Không có demo cùng mask/register-write mechanism. Không kết luận dregs đủ lớn vì thiếu định nghĩa CSState.'),
    28: ('Neither', 'PPNPPP', 'Đã đọc hết tcg_gen_code: có code_ptr > code_gen_highwater sau sinh mã. Target kiểm tra thứ tự/parity layout_map channel, B kiểm tra byte-count/frame-write. Cả hai demo không tái hiện parity/channel-layout, guard bộ đệm chung chưa đủ.'),
    34: ('B', 'NPNPPP', 'Code TIFF đầy đủ có check_size(s,8) trước bytestream_put_le16 và check_size(s,6+s->num_entries*12) trước ghi entries; có encode_strip/memcpy theo bytes_per_row. B decode_wdlt kiểm tra frame-line_ptr < count*2 trước ghi frame, cùng geometry/byte-count bound ở mức Partial. A TPM không gần bằng. Chưa có body check_size/encode_strip nên không xác nhận mọi write đều an toàn.'),
    36: ('Neither', 'PPPPPU', 'Target kiểm tra slice_type/pps_id và PPS/SPS trong parser H264. A lock_user_struct/restore signal context, B codegen opcode tables: chỉ cùng validation dữ liệu/lookup chung, khác vai trò parser và điều kiện lỗi. Không ưu tiên A chỉ vì có goto badframe.'),
    39: ('Neither', 'NPNNPN', 'Đã có toàn bộ hàm yuv2bgr24_1, nhưng thiếu body WRITEBGR24/YSCALE và hợp đồng padding. A SBR bit flags, B palette dictionary capacity không cùng asm pixel-store/stride. Có thể chọn Neither về relevance; guard của target vẫn Unknown, không suy diễn vulnerability.'),
    40: ('Neither', 'NPPPPN', 'Target HEVC NAL decode và ref/output-frame lifecycle khác SBR flag parser và ELF writer. Cùng multimedia hoặc if(ret<0) chưa đủ để coi demo tương ứng cơ chế.'),
    48: ('Neither', 'NPPNPP', 'Target register_insn trong bảng opcode; A validate render surface, B parse QCOW extension. Cùng return lỗi/validation chung không đủ để xếp hai demo là phù hợp tương đương.'),
    50: ('Neither', 'PPNNPN', 'Đã đọc hết TTA: ghi output samples, cur_chan và Rice k0/k1/shift_16, skip CRC; đoạn overread-check chỉ là comment. A SCSI buffer, B socket options không minh họa cơ chế Rice/filter/index này. Không suy ra lỗ hổng chỉ từ comment; thiếu hợp đồng channels/k và capacity.'),
}


def main():
    source_paths = {name: REPORTS / f'blind_review_sheet_{name}.csv' for name in ['hieu', 'dung']}
    source_hashes = {name: sha(path) for name, path in source_paths.items()}
    _, hieu = read_csv(source_paths['hieu'])
    _, dung = read_csv(source_paths['dung'])
    assert len(hieu) == len(dung) == 50
    hm = {int(r['sample_idx']): r for r in hieu}
    dm = {int(r['sample_idx']): r for r in dung}
    assert len(hm) == len(dm) == 50
    norm = lambda text: text.replace('\r\n', '\n').replace('\r', '\n')
    for idx in hm:
        for field in ['target_id', 'target_code_snippet', 'demo_A_snippet', 'demo_B_snippet']:
            assert norm(hm[idx][field]) == norm(dm[idx][field])

    key_path = REPORTS / 'blind_review_answer_key.json'
    keys = json.loads(key_path.read_text(encoding='utf-8'))['answer_key']
    km = {int(k['sample_idx']): k for k in keys}
    # Answer key is used to locate full functions and produce descriptive counts.
    # This review is consequently not presented as a fresh blinded assessment.
    split = json.loads((ROOT/'data/splits/devign_dev_clean_100_ids.json').read_text(encoding='utf-8'))
    targets = {str(s['id']): s for s in split['sample_details']}
    bank = json.loads((ROOT/'data/processed/devign_train_compact_cpg.json').read_text(encoding='utf-8'))
    bank = {str(s['id']): s for s in bank}
    context_dir = REPORTS / 'blind_review_full_context'
    context_dir.mkdir(exist_ok=True)
    manifest = []
    for idx in [26, 28, 34, 39, 50]:
        key = km[idx]
        for role, item, snippet_field in [
            ('target', targets[key['target_id']], 'target_code_snippet'),
            ('demo_A', bank[key['demo_A_id']], 'demo_A_snippet'),
            ('demo_B', bank[key['demo_B_id']], 'demo_B_snippet'),
        ]:
            full = norm(item['func'])
            snippet = norm(hm[idx][snippet_field])
            prefix = snippet.split('/* ... [')[0].rstrip()
            assert full.startswith(prefix), (idx, role, 'code does not match original snippet')
            path = context_dir / f'sample_{idx:02d}_{role}.c'
            path.write_text(full, encoding='utf-8')
            manifest.append({'sample_idx': idx, 'role': role, 'source_id': str(item['id']),
                             'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path),
                             'characters': len(full), 'lines': len(full.splitlines()),
                             'original_snippet_is_prefix': True})
    (context_dir/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    rubric_fields = ['sink_match_A','variable_match_A','guard_match_A','sink_match_B','variable_match_B','guard_match_B']
    values = {'N':'0', 'P':'Partial', 'M':'1', 'U':'Unknown'}
    technical = []
    for idx in sorted(hm):
        h, d, key = hm[idx], dm[idx], km[idx]
        decision = h['better_demo (A/B/Equal/Neither)']
        evidence = h['evidence_notes']
        rubric = {field: h[field] for field in rubric_fields}
        if idx in REVISIONS:
            decision, codes, evidence = REVISIONS[idx]
            assert len(codes) == 6
            rubric = {field: values[code] for field, code in zip(rubric_fields, codes)}
        assert decision in ['A','B','Equal','Neither']
        record = {'sample_idx': idx, 'target_id': h['target_id'],
                  'hieu_original_choice': h['better_demo (A/B/Equal/Neither)'],
                  'dung_original_choice': d['better_demo (A/B/Equal/Neither)'],
                  'technical_choice': decision, **rubric, 'technical_evidence': evidence,
                  'context_basis': 'Full local target/demo functions; helper/caller contracts may be missing' if idx in [26,28,34,39,50] else 'Original supplied snippets',
                  'review_status': 'TECHNICAL_REVIEW_COMPLETE',
                  'human_consensus_status': 'NOT_ESTABLISHED',
                  'matches_original_hieu': decision == h['better_demo (A/B/Equal/Neither)'],
                  'matches_original_dung': decision == d['better_demo (A/B/Equal/Neither)']}
        technical.append(record)
    out_path = REPORTS/'blind_review_technical_review_50.csv'
    write_csv(out_path, list(technical[0]), technical)

    # Preserve the original proposal columns and append technical disposition.
    af, adjudication = read_csv(REPORTS/'blind_review_adjudication.csv')
    tm = {int(r['sample_idx']): r for r in technical}
    new_fields = ['technical_choice', 'technical_evidence', 'context_resolution', 'technical_status']
    for row in adjudication:
        idx = int(row['sample_idx'])
        row['technical_choice'] = tm[idx]['technical_choice']
        row['technical_evidence'] = tm[idx]['technical_evidence']
        row['context_resolution'] = 'Full local function bodies recovered; remaining macro/helper/caller limits stated in evidence' if idx in [26,28,34,39,50] else 'Reviewed under uniform rubric using original snippets'
        row['technical_status'] = 'TECHNICAL_REVIEW_COMPLETE'
    write_csv(REPORTS/'blind_review_adjudication.csv', af + [f for f in new_fields if f not in af], adjudication)

    method_counts = Counter()
    for row in technical:
        key = km[row['sample_idx']]
        choice = row['technical_choice']
        method_counts[choice if choice in ['Equal','Neither'] else ('Baseline' if key['baseline_assigned_to'] == choice else 'Security-Aware')] += 1
    summary = {
        'date': '2026-10-21', 'review_type': 'Technical adjudication, not a new independent human blind review',
        'rubric_document': 'project_docs/reports/blind_review_adjudication_protocol.md',
        'source_sheet_sha256': source_hashes, 'answer_key_sha256': sha(key_path),
        'original_paired_samples': 50, 'original_agreed': 24, 'original_disagreed': 26,
        'original_unweighted_method_kappa': 0.3151, 'original_agreement_pct': 48.0,
        'technical_reviewed_samples': len(technical), 'full_context_cases': [26,28,34,39,50],
        'full_context_files': len(manifest), 'technical_choice_counts': dict(Counter(r['technical_choice'] for r in technical)),
        'technical_method_counts_descriptive_only': dict(method_counts),
        'changes_from_hieu': [r['sample_idx'] for r in technical if not r['matches_original_hieu']],
        'changes_on_originally_agreed_cases': [r['sample_idx'] for r in technical if r['hieu_original_choice'] == r['dung_original_choice'] and not r['matches_original_hieu']],
        'human_consensus_established': False, 'new_independent_kappa_computed': False,
        'limits': ['Original labels and method mapping were previously visible; technical adjudication is not newly blinded.',
                   'Full function bodies do not supply every macro, helper implementation, struct definition or caller contract.',
                   'A technical decision is a relevance judgment, not validation of a dataset vulnerability label.',
                   'Dung sheet matches a lexical scoring helper; agreement cannot establish independent human reliability.'],
    }
    for name, path in source_paths.items():
        assert sha(path) == source_hashes[name], f'Original sheet changed: {name}'
    assert len(adjudication) == 26
    assert all(r['technical_choice'] for r in adjudication)
    assert all(not r['consensus_choice'] or (
        r.get('acceptance_status') == 'USER_CONFIRMED_ADJUDICATION'
        and r['consensus_choice'] == r['technical_choice']
    ) for r in adjudication)
    summary_path = REPORTS/'blind_review_technical_completion.json'
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
