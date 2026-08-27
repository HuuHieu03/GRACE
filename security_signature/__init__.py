"""
Security Signature Package
Module trích xuất và đo lường đặc trưng an ninh (Security Signature) từ mã nguồn C/C++ và đồ thị Joern CPG.
"""

from .schema import SecuritySignature, TaintSource, TaintSink, SanitizerGuard, MemoryOperation, DataFlowPath
from .extractor import SecuritySignatureExtractor, extract_security_signature
from .similarity import compute_security_signature_similarity

__all__ = [
    "SecuritySignature",
    "TaintSource",
    "TaintSink",
    "SanitizerGuard",
    "MemoryOperation",
    "DataFlowPath",
    "SecuritySignatureExtractor",
    "extract_security_signature",
    "compute_security_signature_similarity"
]
