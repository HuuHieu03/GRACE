"""
Security Signature Data Schema
Định nghĩa cấu trúc dữ liệu cho đặc trưng an ninh (Security Signature) của hàm C/C++.
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional


@dataclass
class TaintSource:
    """Đại diện cho nguồn dữ liệu đầu vào (Source) có thể mang dữ liệu không tin cậy."""
    name: str                       # Tên biến / tham số (ví dụ: 'input_buf', 'len')
    source_type: str                # 'parameter', 'network_io', 'file_io', 'user_input'
    node_id: Optional[str] = None   # Node ID trong Joern CPG


@dataclass
class TaintSink:
    """Đại diện cho đích đến nguy hiểm (Sink) dễ phát sinh lỗ hổng bảo mật."""
    api_name: str                   # Tên hàm / thao tác nguy hiểm ('memcpy', 'strcpy', 'free', 'deref')
    sink_category: str              # 'buffer_write', 'pointer_free', 'format_string', 'exec', 'alloc'
    node_id: Optional[str] = None   # Node ID trong Joern CPG
    is_controlled: bool = False     # Có nằm dưới một khối kiểm tra điều kiện (Sanitizer) không?


@dataclass
class SanitizerGuard:
    """Đại diện cho câu lệnh kiểm tra / ràng buộc an toàn (Sanitizer / Validator)."""
    guard_type: str                 # 'bounds_check', 'null_check', 'sizeof_check', 'return_error', 'assert'
    expression: str                 # Biểu thức kiểm tra (ví dụ: 'len < sizeof(buf)', 'ptr != NULL')
    node_id: Optional[str] = None   # Node ID trong Joern CPG


@dataclass
class MemoryOperation:
    """Đại diện cho các thao tác bộ nhớ chi tiết."""
    has_pointer_deref: bool = False # Có giải phóng tham chiếu con trỏ (*ptr, ptr->member)
    has_array_indexing: bool = False# Có truy cập mảng mảng (arr[idx])
    has_dynamic_alloc: bool = False # Có cấp phát động (malloc, calloc)
    has_explicit_free: bool = False # Có giải phóng bộ nhớ (free)
    has_pointer_arithmetic: bool = False # Có toán tử con trỏ (ptr + offset)


@dataclass
class DataFlowPath:
    """Đại diện cho luồng truyền dữ liệu từ Source đến Sink."""
    source_name: str
    sink_name: str
    path_length: int = 1
    is_sanitized: bool = False      # Trên luồng đi có đi qua SanitizerGuard nào không?


@dataclass
class SecuritySignature:
    """
    Biểu diễn tổng thể đặc trưng an ninh (Security Signature) của một hàm C/C++.
    Có khả năng tuần tự hóa (Serialize) sang Dict / JSON và phục vụ đo lường tương đồng.
    """
    func_name: str = ""
    sources: List[TaintSource] = field(default_factory=list)
    sinks: List[TaintSink] = field(default_factory=list)
    sanitizers: List[SanitizerGuard] = field(default_factory=list)
    memory_ops: MemoryOperation = field(default_factory=MemoryOperation)
    dataflow_paths: List[DataFlowPath] = field(default_factory=list)
    
    # Tập hợp các danh mục API và Sanitizer để đối sánh nhanh (Fast Indexing)
    sink_apis: Set[str] = field(default_factory=set)
    sanitizer_types: Set[str] = field(default_factory=set)
    vulnerability_clues: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi SecuritySignature sang dictionary để lưu trữ hoặc hiển thị."""
        return {
            "func_name": self.func_name,
            "sources": [{"name": s.name, "type": s.source_type} for s in self.sources],
            "sinks": [{"api": s.api_name, "category": s.sink_category, "is_controlled": s.is_controlled} for s in self.sinks],
            "sanitizers": [{"type": g.guard_type, "expr": g.expression} for g in self.sanitizers],
            "memory_ops": {
                "ptr_deref": self.memory_ops.has_pointer_deref,
                "array_idx": self.memory_ops.has_array_indexing,
                "alloc": self.memory_ops.has_dynamic_alloc,
                "free": self.memory_ops.has_explicit_free,
                "ptr_arith": self.memory_ops.has_pointer_arithmetic
            },
            "dataflow_paths": [{"src": p.source_name, "sink": p.sink_name, "sanitized": p.is_sanitized} for p in self.dataflow_paths],
            "sink_apis": sorted(list(self.sink_apis)),
            "sanitizer_types": sorted(list(self.sanitizer_types)),
            "vulnerability_clues": sorted(list(self.vulnerability_clues))
        }
