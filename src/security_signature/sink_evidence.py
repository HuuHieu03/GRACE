"""Experimental E1 call-site evidence. Production signatures are unchanged.

This is a conservative lexical C/C++ scanner, not a preprocessor, compiler,
guard analyzer or vulnerability detector. Unknown calls remain inspectable.
Offsets refer to the original string, including comments and line endings.
"""
from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List

from .extractor import SINK_CATEGORIES


# Exact names only. A family records the operation, never its safety.
# Project-wrapper rules are hypotheses to audit, not whole-program summaries.
WRAPPER_RULES = {
    'av_malloc': ('alloc', 'FFmpeg allocation API'),
    'av_mallocz': ('alloc', 'FFmpeg zeroed allocation API'),
    'av_mallocz_array': ('alloc', 'FFmpeg array allocation API'),
    'av_free': ('pointer_free', 'FFmpeg deallocation API'),
    'av_freep': ('pointer_free', 'FFmpeg deallocation through pointer API'),
    'g_malloc': ('alloc', 'GLib allocation API'),
    'g_malloc0': ('alloc', 'GLib zeroed allocation API'),
    'g_free': ('pointer_free', 'GLib deallocation API'),
    'bdrv_pread': ('block_read', 'Explicit block read wrapper; body not expanded'),
    'bdrv_read': ('block_read', 'Explicit sector read wrapper; body not expanded'),
    'bdrv_pwrite': ('block_write', 'Explicit block write wrapper; body not expanded'),
    'get_buffer': ('buffer_read', 'ByteIO buffer-read helper; body not expanded'),
    'avio_read': ('buffer_read', 'AVIO read helper; body not expanded'),
    'av_new_packet': ('alloc', 'Packet allocation API; body not expanded'),
    'bytestream2_get_buffer': ('buffer_read', 'Bytestream buffer-read helper'),
    'bytestream_put_buffer': ('buffer_write', 'Bytestream buffer-write helper'),
    'lremovexattr': ('filesystem_metadata_write', 'Path extended-attribute removal API'),
}

_NONCODE = re.compile(r'//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|\'(?:\\[\s\S]|[^\'\\])*\'')
_TOKEN = re.compile(r'[A-Za-z_]\w*|->|::|&&|\|\||[^\s]')
_IDENT = re.compile(r'^[A-Za-z_]\w*$')
_CONTROL = {'if','for','while','switch','sizeof','alignof','_Alignof','decltype','catch','static_assert','_Static_assert'}
_NON_TYPE = {'return','throw','co_return','case','else','goto'}


@dataclass(frozen=True)
class CallEvidence:
    api_name: str
    family: str
    start: int
    end: int
    line: int
    expression: str
    evidence_source: str
    status: str
    reason: str


def mask_noncode(code: str) -> str:
    """Preserve offsets/newlines while masking comments, literals, directives."""
    masked = _NONCODE.sub(lambda m: ''.join(c if c in '\r\n' else ' ' for c in m.group()), code)
    lines = masked.splitlines(keepends=True)
    continuation = False
    for idx, line in enumerate(lines):
        directive = continuation or line.lstrip().startswith('#')
        continuation = directive and line.rstrip('\r\n').rstrip().endswith('\\')
        if directive:
            lines[idx] = ''.join(c if c in '\r\n' else ' ' for c in line)
    return ''.join(lines)


def extract_sink_evidence(code: str) -> Dict[str, Any]:
    """Extract evidence from code alone; no IDs, labels, graphs or score inputs."""
    masked = mask_noncode(code)
    tokens = [(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(masked)]
    pairs = {}
    stack = []
    for idx, (token, _, _) in enumerate(tokens):
        if token == '(':
            stack.append(idx)
        elif token == ')' and stack:
            pairs[stack.pop()] = idx
    calls: List[CallEvidence] = []
    diagnostics = []
    for idx, (name, start, _) in enumerate(tokens[:-1]):
        if not _IDENT.fullmatch(name) or name in _CONTROL or tokens[idx+1][0] != '(':
            continue
        closing = pairs.get(idx+1)
        if closing is None:
            diagnostics.append({'name': name, 'start': start, 'reason': 'unbalanced_call_or_declaration'})
            continue
        after = tokens[closing+1][0] if closing+1 < len(tokens) else ''
        # Ordinary function definitions are not call-sites.
        if after == '{':
            continue
        boundary = idx-1
        while boundary >= 0 and tokens[boundary][0] not in {';', '{', '}'}:
            boundary -= 1
        prefix = [t[0] for t in tokens[boundary+1:idx]]
        # At statement start, a type-like prefix followed by (...) ; is a
        # prototype/declaration, including typedef return types and pointers.
        type_like = bool(prefix) and all(_IDENT.fullmatch(t) or t in {'*','&','::'} for t in prefix)
        if after == ';' and type_like and '::' not in prefix and not any(t in _NON_TYPE for t in prefix):
            continue
        preceding = tokens[idx-1][0] if idx else ''
        end = tokens[closing][2]
        source = 'direct_call_site'
        if preceding in {'.','->','::'}:
            family, status, reason = '', 'unknown', 'member_or_qualified_call_requires_resolution'
        elif name in WRAPPER_RULES:
            family, reason = WRAPPER_RULES[name]
            status, source = 'recognized', 'explicit_wrapper_call_site'
        elif name in SINK_CATEGORIES:
            family, status, reason = SINK_CATEGORIES[name], 'recognized', 'registered_API_at_call_site'
        else:
            family, status = '', 'unknown'
            reason = 'unexpanded_macro_or_uppercase_helper' if name.isupper() else 'unresolved_helper_or_function'
        calls.append(CallEvidence(name, family, start, end, code.count('\n',0,start)+1,
                                  code[start:end], source, status, reason))
    recognized = [asdict(c) for c in calls if c.status == 'recognized']
    unknown = [asdict(c) for c in calls if c.status == 'unknown']
    return {'schema_version': 1, 'extractor': 'E1_lexical_callsite_experimental',
            'recognized': recognized, 'unknown_calls': unknown,
            'sink_apis': sorted({c['api_name'] for c in recognized}),
            'sink_families': sorted({c['family'] for c in recognized}),
            'diagnostics': diagnostics,
            'guard_assessment': 'not_performed',
            'limits': ['No macro expansion, type resolution, indirect-call resolution, preprocessor branch evaluation or guard/dataflow proof.',
                       'Missing evidence does not mean no sink or safe code; wrapper rules need semantic validation.']}
