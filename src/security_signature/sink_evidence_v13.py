"""E1.3 experimental syntax exclusions and explicit output-role evidence.

No new API rules, guard claims or production integration. E1.2 remains frozen.
"""
import re

from .sink_evidence import mask_noncode
from .sink_evidence_v12 import extract_sink_evidence as extract_e12

_SCALAR_TYPES = {'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t',
                 'int8_t', 'int16_t', 'int32_t', 'int64_t', 'char', 'int', 'long', 'short'}


def output_role(row, masked):
    name = row['api_name']
    expression = masked[row['start']:row['end']]
    if name in {'sprintf', 'snprintf', 'vsprintf', 'vsnprintf'}:
        return 'buffer_formatting'
    if name in {'fprintf', 'vfprintf'}:
        match = re.match(r'\w+\s*\(\s*(stderr|stdout)\s*,', expression)
        if match:
            return 'diagnostic_stderr' if match.group(1) == 'stderr' else 'standard_stdout'
        return 'stream_output_unresolved'
    if name in {'printf', 'vprintf'}:
        return 'standard_stdout'
    return 'not_assessed'


def extract_sink_evidence(code):
    result = extract_e12(code)
    masked = mask_noncode(code)
    body = masked.find('{')
    excluded = []
    for field in ['recognized', 'unknown_calls']:
        retained = []
        for row in result[field]:
            name, start, end = row['api_name'], row['start'], row['end']
            reason = None
            # Narrow declaration-only patterns: never remove a body call just
            # because its name resembles a type or a macro.
            if body >= 0 and start < body:
                suffix = masked[end:body].lstrip()
                expression = masked[start:end]
                if (name in _SCALAR_TYPES and suffix.startswith('[')
                        and re.fullmatch(r'\w+\s*\(\s*\*\s*[A-Za-z_]\w*\s*\)', expression)):
                    reason = 'array_pointer_parameter_type_not_call'
                elif (name == 'RENAME' and suffix.startswith('(')
                      and re.fullmatch(r'RENAME\s*\(\s*[A-Za-z_]\w*\s*\)', expression)):
                    reason = 'macro_decorated_function_declaration_not_call'
            if reason:
                excluded.append({**row, 'status': 'excluded_syntax', 'exclusion_reason': reason})
            else:
                retained.append({**row, 'output_role': output_role(row, masked),
                                 'role_assessment': 'explicit_syntax_only; purpose_and_guard_not_proven'})
        result[field] = retained
    result.update(extractor='E1.3_syntax_and_output_role_experimental',
                  excluded_syntax=sorted(excluded, key=lambda r: r['start']),
                  sink_apis=sorted({r['api_name'] for r in result['recognized']}),
                  sink_families=sorted({r['family'] for r in result['recognized']}))
    result['limits'] += ['Output roles describe syntax, not main-operation relevance or vulnerability.',
                         'No macro expansion, indirect/asm memory modeling or new wrapper contracts.',
                         'Declaration exclusions cover narrow observed patterns, not a complete C parser.']
    return result
