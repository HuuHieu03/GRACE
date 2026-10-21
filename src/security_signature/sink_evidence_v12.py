"""E1.2: conservative three-valued preprocessor evidence over frozen E1.1.

Only literal integers, !, &&, ||, parentheses and unknown identifiers/defined
are understood. Unknown build configurations remain conditional. This is not
a complete C preprocessor and performs no macro expansion or guard analysis.
"""
from bisect import bisect_right
from dataclasses import dataclass
import re

from .sink_evidence import _NONCODE
from .sink_evidence_v11 import extract_sink_evidence as extract_e11


def _and(left, right):
    return False if left is False or right is False else (True if left is True and right is True else None)


def _or(left, right):
    return True if left is True or right is True else (False if left is False and right is False else None)


def _not(value):
    return None if value is None else not value


_EXPR_TOKEN = re.compile(r'\s*(\|\||&&|!|\(|\)|0[xX][0-9a-fA-F]+[uUlL]*|0[bB][01]+[uUlL]*|[0-9]+[uUlL]*|[A-Za-z_]\w*)')


def evaluate_condition(expression):
    """Return True/False/None; unsupported syntax cannot prove inactivity."""
    tokens=[]
    offset=0
    expression=expression.strip()
    while offset<len(expression):
        match=_EXPR_TOKEN.match(expression,offset)
        if not match or len(tokens)>=512:
            return None
        tokens.append(match.group(1));offset=match.end()
    cursor=0

    def atom():
        nonlocal cursor
        if cursor>=len(tokens):
            raise ValueError('missing operand')
        token=tokens[cursor];cursor+=1
        if token=='!':
            return _not(atom())
        if token=='(':
            value=disjunction()
            if cursor>=len(tokens) or tokens[cursor]!=')':
                raise ValueError('unbalanced expression')
            cursor+=1
            return value
        if token=='defined':
            if cursor<len(tokens) and tokens[cursor]=='(':
                cursor+=1
                if cursor>=len(tokens) or not re.fullmatch(r'[A-Za-z_]\w*',tokens[cursor]):
                    raise ValueError('invalid defined operand')
                cursor+=1
                if cursor>=len(tokens) or tokens[cursor]!=')':
                    raise ValueError('invalid defined expression')
                cursor+=1
            else:
                if cursor>=len(tokens) or not re.fullmatch(r'[A-Za-z_]\w*',tokens[cursor]):
                    raise ValueError('invalid defined operand')
                cursor+=1
            return None
        if re.fullmatch(r'[A-Za-z_]\w*',token):
            return None
        number=re.sub(r'[uUlL]+$','',token)
        if number.startswith(('0x','0X','0b','0B')):
            return int(number,0)!=0
        if number.isdigit():
            return int(number,8 if len(number)>1 and number.startswith('0') else 10)!=0
        raise ValueError('unsupported operand')

    def conjunction():
        nonlocal cursor
        value=atom()
        while cursor<len(tokens) and tokens[cursor]=='&&':
            cursor+=1;value=_and(value,atom())
        return value

    def disjunction():
        nonlocal cursor
        value=conjunction()
        while cursor<len(tokens) and tokens[cursor]=='||':
            cursor+=1;value=_or(value,conjunction())
        return value

    try:
        result=disjunction()
        return result if cursor==len(tokens) else None
    except (ValueError,RecursionError):
        return None


@dataclass
class _Frame:
    parent: object
    taken: object
    opening: int
    branch: str
    seen_else: bool=False


def preprocessor_regions(code):
    """Offset-preserving regions and diagnostics for conditional directives."""
    clean=_NONCODE.sub(lambda m: ''.join(c if c in '\r\n' else ' ' for c in m.group()),code)
    physical=clean.splitlines(keepends=True)
    regions=[]
    diagnostics=[]
    stack=[]
    state=True
    offset=0
    idx=0
    while idx<len(physical):
        start=offset
        line=physical[idx]
        offset+=len(line);idx+=1
        logical=line
        if line.lstrip().startswith('#'):
            while logical.rstrip('\r\n').endswith('\\') and idx<len(physical):
                logical=logical.rstrip('\r\n')[:-1]+physical[idx]
                offset+=len(physical[idx]);idx+=1
        regions.append({'start':start,'end':offset,'value':state,
                        'conditions':[frame.branch for frame in stack]})
        directive=re.match(r'^\s*#\s*(\w+)\b(.*)',logical,re.DOTALL)
        if not directive:
            continue
        name,argument=directive.group(1),directive.group(2).strip()
        if name in {'if','ifdef','ifndef'}:
            condition=evaluate_condition(argument) if name=='if' else None
            stack.append(_Frame(state,condition,start,'#'+name+' '+argument))
            state=_and(state,condition)
        elif name in {'elif','elifdef','elifndef'}:
            if not stack:
                diagnostics.append({'start':start,'reason':'orphan_'+name});continue
            frame=stack[-1]
            if frame.seen_else:
                diagnostics.append({'start':start,'reason':'elif_after_else'})
                state=_and(frame.parent,None);continue
            condition=evaluate_condition(argument) if name=='elif' else None
            state=_and(frame.parent,_and(_not(frame.taken),condition))
            frame.branch='#'+name+' '+argument
            frame.taken=_or(frame.taken,condition)
        elif name=='else':
            if not stack:
                diagnostics.append({'start':start,'reason':'orphan_else'});continue
            frame=stack[-1]
            if frame.seen_else:
                diagnostics.append({'start':start,'reason':'duplicate_else'})
                state=_and(frame.parent,None);continue
            state=_and(frame.parent,_not(frame.taken))
            frame.branch='#else (after previous branches)'
            frame.taken=True;frame.seen_else=True
        elif name=='endif':
            if stack:
                state=stack.pop().parent
            else:
                diagnostics.append({'start':start,'reason':'orphan_endif'})
    if stack:
        # Invalid/incomplete input must not acquire false certainty from an
        # unterminated conditional; retain the affected text as conditional.
        opening=min(frame.opening for frame in stack)
        diagnostics.append({'start':opening,'reason':'unclosed_conditional'})
        for region in regions:
            if region['start']>=opening:
                region['value']=None
    return regions,diagnostics


def extract_sink_evidence(code):
    regions,diagnostics=preprocessor_regions(code)
    starts=[row['start'] for row in regions]

    def context(start):
        index=bisect_right(starts,start)-1
        if index<0:
            return {'value':True,'conditions':[]}
        return regions[index]

    chars=list(code)
    for region in regions:
        if region['value'] is False:
            for index in range(region['start'],region['end']):
                if chars[index] not in '\r\n':
                    chars[index]=' '
    # Remove known-dead text before parsing so invalid code there cannot
    # corrupt bracket matching of the potentially active source.
    result=extract_e11(''.join(chars))
    for key in ['recognized','unknown_calls']:
        for row in result[key]:
            region=context(row['start'])
            first=max(0,bisect_right(starts,row['start'])-1)
            last=bisect_right(starts,row['end']-1)
            crossed=regions[first:last]
            conditional=region['value'] is None or any(part['value'] is None for part in crossed)
            row['expression']=code[row['start']:row['end']]
            row['preprocessor_state']='conditional' if conditional else 'active'
            row['preprocessor_conditions']=list(dict.fromkeys(
                condition for part in crossed for condition in part['conditions']))
    # Keep an audit record of original call candidates excluded by proof of
    # inactivity; these are not used to construct sink_apis/families.
    original=extract_e11(code)
    inactive=[]
    for key in ['recognized','unknown_calls']:
        for row in original[key]:
            region=context(row['start'])
            if region['value'] is False:
                inactive.append({**row,'status':'excluded_inactive',
                                 'original_status':row['status'],
                                 'preprocessor_state':'inactive',
                                 'preprocessor_conditions':list(region['conditions'])})
    result.update(
        extractor='E1.2_preprocessor_aware_experimental',
        inactive_calls=sorted(inactive,key=lambda row:row['start']),
        preprocessor_diagnostics=diagnostics,
        unconditional_sink_apis=sorted({row['api_name'] for row in result['recognized'] if row['preprocessor_state']=='active'}),
        conditional_sink_apis=sorted({row['api_name'] for row in result['recognized'] if row['preprocessor_state']=='conditional'}),
    )
    result['limits']=[limit.replace('preprocessor branch evaluation','full preprocessor evaluation')
                      for limit in result['limits']]+[
        'sink_apis/families include potentially active conditional sites; inspect preprocessor_state before treating evidence as unconditional.',
        'No build configuration, macro expansion or unsupported arithmetic/comparison evaluation; those conditions remain unknown.',
    ]
    return result
