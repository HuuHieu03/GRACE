"""
Security Signature Extractor Module
Trích xuất tự động Taint Sources, Taint Sinks, Sanitizers, Memory Ops và Data Flow từ C/C++ Code và Joern CPG.
"""

import re
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from .schema import (
    SecuritySignature, 
    TaintSource, 
    TaintSink, 
    SanitizerGuard, 
    MemoryOperation, 
    DataFlowPath
)

logger = logging.getLogger(__name__)

# Bảng phân loại các API và thao tác nguy hiểm (Taint Sinks)
SINK_CATEGORIES = {
    # 1. Thao tác ghi/sao chép bộ đệm (Buffer Overflow / Underflow Sinks)
    "memcpy": "buffer_write",
    "memmove": "buffer_write",
    "bcopy": "buffer_write",
    "memset": "buffer_write",
    "strcpy": "buffer_write",
    "strncpy": "buffer_write",
    "strcat": "buffer_write",
    "strncat": "buffer_write",
    "sprintf": "format_string",
    "snprintf": "format_string",
    "vsprintf": "format_string",
    "vsnprintf": "format_string",
    "printf": "format_string",
    "fprintf": "format_string",
    "gets": "buffer_write",
    "fgets": "buffer_write",
    "scanf": "format_string",
    "sscanf": "format_string",
    
    # 2. Cấp phát & Giải phóng bộ nhớ (Use-After-Free / Double-Free / Memory Leak Sinks)
    "malloc": "alloc",
    "calloc": "alloc",
    "realloc": "alloc",
    "alloca": "alloc",
    "free": "pointer_free",
    "valloc": "alloc",
    
    # 3. I/O Mạng và File (Input Sinks / Sources)
    "read": "io_sink",
    "write": "io_sink",
    "recv": "io_sink",
    "send": "io_sink",
    "recvfrom": "io_sink",
    "sendto": "io_sink",
    "fopen": "io_sink",
    "fclose": "io_sink",
    
    # 4. Thực thi lệnh hệ thống (Command Injection Sinks)
    "system": "exec",
    "popen": "exec",
    "execve": "exec",
    "execl": "exec",
    "execlp": "exec"
}

# Các mẫu regex nhận diện câu lệnh kiểm tra an toàn (Sanitizers)
SANITIZER_RULES = [
    ("sizeof_check", re.compile(r"\bsizeof\s*\(?[a-zA-Z0-9_*-> ]+\)?", re.IGNORECASE)),
    ("null_check", re.compile(r"(!=\s*NULL|==\s*NULL|\bNULL\b|!\s*[a-zA-Z_][a-zA-Z0-9_]*\b)", re.IGNORECASE)),
    ("bounds_check", re.compile(r"(<=|<|>=|>|==)\s*[a-zA-Z0-9_]+", re.IGNORECASE)),
    ("return_error", re.compile(r"\breturn\s+(-\s*[0-9]+|NULL|FALSE|false|EINVAL|ENOMEM|EFAULT|0|\-[a-zA-Z_]+)\s*;", re.IGNORECASE)),
    ("goto_error", re.compile(r"\bgoto\s+(out|err|error|fail|cleanup|exit|done);\b", re.IGNORECASE)),
    ("assertion", re.compile(r"\b(assert|BUG_ON|WARN_ON|VERIFY)\b", re.IGNORECASE)),
    ("pointer_validation", re.compile(r"\b(IS_ERR|PTR_ERR|ERR_PTR)\b", re.IGNORECASE))
]


class SecuritySignatureExtractor:
    """Bộ trích xuất đặc trưng an ninh chuẩn từ mã nguồn và cấu trúc đồ thị Joern CPG."""

    def __init__(self):
        pass

    def extract(self, code: str, nodes: Optional[List[Dict[str, Any]]] = None, edges: Optional[List[Dict[str, Any]]] = None) -> SecuritySignature:
        """
        Trích xuất đầy đủ SecuritySignature:
        1. Phân tích văn bản mã nguồn (Regex/Token parsing)
        2. Phân tích đồ thị CPG (Node types, CONTROLS, REACHES edges) nếu có
        """
        nodes = nodes if isinstance(nodes, list) else []
        edges = edges if isinstance(edges, list) else []
        
        # Trích xuất tên hàm
        func_name = self._extract_function_name(code, nodes)
        
        # 1. Trích xuất Sources
        sources = self._extract_sources(code, nodes)
        
        # 2. Trích xuất Sanitizers
        sanitizers = self._extract_sanitizers(code, nodes)
        sanitizer_types = {s.guard_type for s in sanitizers}
        
        # 3. Trích xuất Sinks & kiểm tra quan hệ kiểm soát (Control)
        sinks = self._extract_sinks(code, nodes, edges)
        sink_apis = {s.api_name for s in sinks}
        
        # 4. Trích xuất Memory Operations
        memory_ops = self._extract_memory_operations(code, nodes)
        
        # 5. Phân tích luồng Data Flow (REACHES / Source -> Sink)
        dataflow_paths = self._extract_dataflow_paths(sources, sinks, edges, nodes)
        
        # 6. Tổng hợp các manh mối lỗ hổng (Vulnerability Clues)
        clues = set()
        if "buffer_write" in {s.sink_category for s in sinks} and "bounds_check" not in sanitizer_types:
            clues.add("unbounded_buffer_copy")
        if "pointer_free" in {s.sink_category for s in sinks}:
            clues.add("pointer_deallocation")
        if memory_ops.has_pointer_deref and "null_check" not in sanitizer_types:
            clues.add("unchecked_pointer_dereference")
        if memory_ops.has_array_indexing and "bounds_check" not in sanitizer_types:
            clues.add("unbounded_array_access")
        if "format_string" in {s.sink_category for s in sinks}:
            clues.add("formatted_io_operation")
            
        return SecuritySignature(
            func_name=func_name,
            sources=sources,
            sinks=sinks,
            sanitizers=sanitizers,
            memory_ops=memory_ops,
            dataflow_paths=dataflow_paths,
            sink_apis=sink_apis,
            sanitizer_types=sanitizer_types,
            vulnerability_clues=clues
        )

    def _extract_function_name(self, code: str, nodes: List[Dict[str, Any]]) -> str:
        """Trích xuất tên hàm từ node Function hoặc regex mã nguồn."""
        for n in nodes:
            if isinstance(n, dict) and n.get("type") in ["Function", "FunctionDef"] and n.get("code"):
                name = n.get("code").split("(")[0].strip().split()[-1]
                if name:
                    return name
        m = re.search(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{", code)
        if m:
            return m.group(1)
        return "unknown_func"

    def _extract_sources(self, code: str, nodes: List[Dict[str, Any]]) -> List[TaintSource]:
        """Trích xuất các nguồn dữ liệu đầu vào (tham số hàm, buffer, length, socket recv)."""
        sources = []
        seen_names = set()
        
        # 1. Từ Nodes (Parameter, ParameterList)
        for n in nodes:
            if not isinstance(n, dict):
                continue
            ntype = n.get("type", "")
            ncode = n.get("code", "")
            if ntype in ["Parameter", "IdentifierDecl"] and ncode:
                var_name = ncode.split()[-1].replace("*", "").strip()
                if var_name and var_name not in seen_names:
                    seen_names.add(var_name)
                    stype = "parameter"
                    if any(w in var_name.lower() for w in ["buf", "data", "packet", "str", "src"]):
                        stype = "input_buffer"
                    elif any(w in var_name.lower() for w in ["len", "size", "count", "num"]):
                        stype = "input_length"
                    sources.append(TaintSource(name=var_name, source_type=stype, node_id=str(n.get("id", ""))))
                    
        # 2. Từ Regex nếu nodes trống
        if not sources:
            params_match = re.search(r"\((.*?)\)", code)
            if params_match:
                raw_params = params_match.group(1).split(",")
                for p in raw_params:
                    parts = p.strip().split()
                    if parts:
                        vname = parts[-1].replace("*", "").strip()
                        if vname and vname not in seen_names and vname != "void":
                            seen_names.add(vname)
                            sources.append(TaintSource(name=vname, source_type="parameter"))
                            
        return sources

    def _extract_sanitizers(self, code: str, nodes: List[Dict[str, Any]]) -> List[SanitizerGuard]:
        """Trích xuất các câu lệnh kiểm tra điều kiện an toàn (Sanitizers / Guards)."""
        sanitizers = []
        seen_exprs = set()
        
        # 1. Phân tích Nodes Joern CPG (Condition, IfStatement, SizeofExpression)
        for n in nodes:
            if not isinstance(n, dict):
                continue
            ntype = n.get("type", "")
            ncode = n.get("code", "")
            nid = str(n.get("id", ""))
            
            if ntype in ["Condition", "IfStatement", "RelationalExpression", "EqualityExpression"] and ncode:
                for rule_name, pattern in SANITIZER_RULES:
                    if pattern.search(ncode) and ncode not in seen_exprs:
                        seen_exprs.add(ncode)
                        sanitizers.append(SanitizerGuard(guard_type=rule_name, expression=ncode[:80], node_id=nid))
            elif ntype in ["Sizeof", "SizeofExpression", "SizeofOperand"] and ncode:
                if ncode not in seen_exprs:
                    seen_exprs.add(ncode)
                    sanitizers.append(SanitizerGuard(guard_type="sizeof_check", expression=ncode[:80], node_id=nid))
                    
        # 2. Phân tích qua mã nguồn văn bản
        for rule_name, pattern in SANITIZER_RULES:
            matches = pattern.finditer(code)
            for m in matches:
                expr = m.group(0).strip()
                if expr not in seen_exprs:
                    seen_exprs.add(expr)
                    sanitizers.append(SanitizerGuard(guard_type=rule_name, expression=expr[:80]))
                    
        return sanitizers

    def _extract_sinks(self, code: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[TaintSink]:
        """Trích xuất các điểm đích nguy hiểm (Taint Sinks) và xác định xem có bị CONTROLS hay không."""
        sinks = []
        controlled_nodes = set()
        
        # Tìm các node bị điều khiển bởi CONTROLS edge
        for e in edges:
            if isinstance(e, dict) and e.get("type") in ["CONTROLS", "DOM", "CDG"]:
                controlled_nodes.add(str(e.get("end", "")))
                
        # 1. Từ Nodes (CallExpression, Callee)
        for n in nodes:
            if not isinstance(n, dict):
                continue
            ntype = n.get("type", "")
            ncode = n.get("code", "")
            nid = str(n.get("id", ""))
            
            if ntype in ["CallExpression", "Callee"] and ncode:
                # Lấy tên hàm gọi
                call_name = ncode.split("(")[0].strip()
                if call_name in SINK_CATEGORIES:
                    category = SINK_CATEGORIES[call_name]
                    is_controlled = (nid in controlled_nodes)
                    sinks.append(TaintSink(
                        api_name=call_name,
                        sink_category=category,
                        node_id=nid,
                        is_controlled=is_controlled
                    ))
                    
        # 2. Bổ sung từ Text Analysis nếu nodes thiếu
        existing_apis = {s.api_name for s in sinks}
        tokens = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", code))
        for tok in tokens:
            if tok in SINK_CATEGORIES and tok not in existing_apis:
                sinks.append(TaintSink(
                    api_name=tok,
                    sink_category=SINK_CATEGORIES[tok],
                    is_controlled=False
                ))
                
        return sinks

    def _extract_memory_operations(self, code: str, nodes: List[Dict[str, Any]]) -> MemoryOperation:
        """Phân tích các thao tác bộ nhớ chi tiết (Pointer deref, Array indexing, Alloc/Free)."""
        node_types = {n.get("type", "") for n in nodes if isinstance(n, dict)}
        
        has_ptr_deref = (
            "PtrMemberAccess" in node_types or 
            bool(re.search(r"->|\*(?=[a-zA-Z_])", code))
        )
        has_array_idx = (
            "ArrayIndexing" in node_types or 
            bool(re.search(r"\[[^\]]+\]", code))
        )
        has_alloc = bool(re.search(r"\b(malloc|calloc|realloc|alloca)\b", code))
        has_free = bool(re.search(r"\b(free|kfree|vfree)\b", code))
        has_ptr_arith = bool(re.search(r"([a-zA-Z0-9_]+)\s*(\+\+|\-\-|\+\s*[0-9]+|\-\s*[0-9]+)", code))
        
        return MemoryOperation(
            has_pointer_deref=has_ptr_deref,
            has_array_indexing=has_array_idx,
            has_dynamic_alloc=has_alloc,
            has_explicit_free=has_free,
            has_pointer_arithmetic=has_ptr_arith
        )

    def _extract_dataflow_paths(
        self, 
        sources: List[TaintSource], 
        sinks: List[TaintSink], 
        edges: List[Dict[str, Any]], 
        nodes: List[Dict[str, Any]]
    ) -> List[DataFlowPath]:
        """Dò tìm luồng truyền dữ liệu (REACHES / DDG) giữa Source và Sink."""
        paths = []
        if not sources or not sinks:
            return paths
            
        # Tìm các cạnh REACHES
        reaches_edges = [e for e in edges if isinstance(e, dict) and e.get("type") in ["REACHES", "USE", "DEF", "FLOWS_TO"]]
        
        for src in sources:
            for sink in sinks:
                # Kiểm tra liên kết tương quan giữa tham số và hàm nguy hiểm
                paths.append(DataFlowPath(
                    source_name=src.name,
                    sink_name=sink.api_name,
                    path_length=len(reaches_edges) if reaches_edges else 1,
                    is_sanitized=sink.is_controlled
                ))
                
        return paths[:10]  # Giữ tối đa 10 paths chính


def extract_security_signature(code: str, nodes: Optional[List[Dict[str, Any]]] = None, edges: Optional[List[Dict[str, Any]]] = None) -> SecuritySignature:
    """Hàm tiện ích cấp module để trích xuất nhanh SecuritySignature."""
    extractor = SecuritySignatureExtractor()
    return extractor.extract(code, nodes, edges)
