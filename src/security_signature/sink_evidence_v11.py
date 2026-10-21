"""E1.1: exact-name wrapper registry extension of the frozen E1 scanner.

Experimental operation evidence only. Neither production extraction nor the
frozen E1 source/registry is modified. Rules are based on caller-context review,
not independent proofs of wrapper implementations or vulnerability relevance.
"""
import hashlib
import json
from types import MappingProxyType

from .sink_evidence import extract_sink_evidence as extract_e1


NEW_WRAPPER_RULES = MappingProxyType({
    'av_fast_padded_malloc': 'alloc',
    'av_frame_alloc': 'alloc',
    'av_free_packet': 'pointer_free',
    'av_metadata_free': 'pointer_free',
    'av_realloc': 'alloc',
    'av_strlcat': 'buffer_write',
    'avformat_free_context': 'pointer_free',
    'bytestream2_get_byte': 'buffer_read',
    'close': 'io_close',
    'fchmod': 'filesystem_metadata_write',
    'fchownat': 'filesystem_metadata_write',
    'ff_thread_get_buffer': 'alloc',
    'g_new': 'alloc',
    'g_strdup': 'alloc',
    'openat': 'io_open',
    'qemu_get_be32s': 'buffer_read',
    'qemu_get_sbe32s': 'buffer_read',
    'qemu_iovec_from_buf': 'buffer_write',
    'qemu_mallocz': 'alloc',
    'tcg_malloc': 'alloc',
    'url_close': 'io_close',
    'url_close_dyn_buf': 'io_close',
    'url_fclose': 'io_close',
    'url_fopen': 'io_open',
    'virtio_scsi_free_req': 'pointer_free',
})

REGISTRY_SHA256 = hashlib.sha256(
    json.dumps(dict(NEW_WRAPPER_RULES), sort_keys=True).encode('utf-8')
).hexdigest()


def extract_sink_evidence(code: str):
    """Run unchanged E1 parsing, then classify eligible Unknown call-sites."""
    result = extract_e1(code)
    recognized = list(result['recognized'])
    unknown = []
    for row in result['unknown_calls']:
        # Member/qualified calls must not be interpreted as library APIs.
        if (row['api_name'] in NEW_WRAPPER_RULES
                and row['evidence_source'] == 'direct_call_site'
                and row['reason'] == 'unresolved_helper_or_function'):
            promoted = dict(row)
            promoted.update(
                family=NEW_WRAPPER_RULES[row['api_name']],
                status='recognized',
                evidence_source='exact_wrapper_call_site_v11',
                reason='exact_name_rule_from_technical_caller_context_review',
                rule_id='E1.1:' + row['api_name'],
                semantic_validation='caller_context_only; wrapper_contract_not_independently_audited',
            )
            recognized.append(promoted)
        else:
            unknown.append(row)
    recognized.sort(key=lambda row: (row['start'], row['end']))
    result.update(
        extractor='E1.1_exact_wrapper_extension_experimental',
        registry_sha256=REGISTRY_SHA256,
        recognized=recognized,
        unknown_calls=unknown,
        sink_apis=sorted({row['api_name'] for row in recognized}),
        sink_families=sorted({row['family'] for row in recognized}),
    )
    result['limits'] = result['limits'] + [
        'E1.1 rules were designed using H1 dev50 annotations; performance there is regression fit, not held-out validation.',
        'A family describes an operation, not a taint path, effective guard, guaranteed allocation/free effect or vulnerability.',
    ]
    return result
