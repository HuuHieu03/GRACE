"""
GRACE Token Budget Manager
Module quản lý ngân sách ngữ cảnh (Context Budget) bằng Token của mô hình (Pluggable Token Budgeting).

Đặc tả:
- Tokenizer tham chiếu mặc định: Qwen/Qwen2.5-Coder-32B-Instruct
- Cơ chế Offline Fallback an toàn (không phụ thuộc kết nối HuggingFace)
- Phân bổ ngân sách:
  * target_code <= 3000 tokens
  * graph <= 1500 tokens
  * demonstration <= 1500 tokens
  * output_reserve = 64 tokens
  * total <= 8192 tokens
- Cắt tỉa token an toàn (Safe Token Truncation) và phát hiện cắt rỗng:
  * Đánh dấu flag truncated_demo = True nếu demo bị cắt > 75% độ dài hoặc rỗng
- Thống kê chi tiết: tokens_code, tokens_graph, tokens_demo, tokens_instruction, tokens_total
"""

import logging
import os
import re
import socket
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


_NETWORK_AVAILABLE_CACHE: Dict[Tuple[str, int], bool] = {}


def _is_network_available(
    host: str = "huggingface.co",
    port: int = 443,
    timeout: float = 0.2,
    force_refresh: bool = False,
) -> bool:
    """Kiểm tra kết nối mạng nhanh tới HuggingFace để không làm treo tiến trình khi offline."""
    if os.environ.get("HF_HUB_OFFLINE") == "1" or os.environ.get("TRANSFORMERS_OFFLINE") == "1":
        return False
    cache_key = (host, port)
    if not force_refresh and cache_key in _NETWORK_AVAILABLE_CACHE:
        return _NETWORK_AVAILABLE_CACHE[cache_key]
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        _NETWORK_AVAILABLE_CACHE[cache_key] = True
        return True
    except (socket.error, OSError):
        _NETWORK_AVAILABLE_CACHE[cache_key] = False
        return False


def _is_model_locally_cached(tokenizer_name: str) -> bool:
    """Kiểm tra nhanh xem tokenizer đã có sẵn trên máy (local directory hoặc hub cache) chưa."""
    if not tokenizer_name:
        return False
    if os.path.exists(tokenizer_name):
        return True
    hf_hub = os.environ.get("HF_HUB_CACHE") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if not hf_hub:
        hf_home = os.environ.get("HF_HOME")
        if hf_home:
            hf_hub = os.path.join(hf_home, "hub")
        else:
            hf_hub = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
    repo_folder = f"models--{tokenizer_name.replace('/', '--')}"
    target_dir = os.path.join(hf_hub, repo_folder)
    if not os.path.isdir(target_dir):
        return False
    snapshots_dir = os.path.join(target_dir, "snapshots")
    if not os.path.isdir(snapshots_dir):
        return False
    try:
        entries = os.listdir(snapshots_dir)
        return len(entries) > 0
    except OSError:
        return False


class TruncateResult(tuple):
    """Tuple 4 phần tử tương thích ngược hoàn toàn, kèm thuộc tính truncated_core và cut_char_index."""
    def __new__(cls, result: str, was_truncated: bool, orig_tokens: int, kept_tokens: int, truncated_core: str):
        obj = super().__new__(cls, (result, was_truncated, orig_tokens, kept_tokens))
        obj.truncated_core = truncated_core
        obj.cut_char_index = len(truncated_core)
        return obj


class OfflineFallbackTokenizer:
    """
    Tokenizer xấp xỉ ngoại tuyến (Offline Fallback) cho C/C++ và văn bản tự nhiên.
    Đảm bảo tính toán độc lập, không cần mạng, lossless roundtrip trên 100% Unicode:
    ''.join(tokenize(text)) == text.
    """
    TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]|\s+")

    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        return self.TOKEN_PATTERN.findall(text)

    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        tokens = self.tokenize(text)
        return [abs(hash(tok)) % 1000000 for tok in tokens]

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.tokenize(text))

    def truncate(self, text: str, max_tokens: int) -> str:
        if not text or max_tokens <= 0:
            return ""
        tokens = self.tokenize(text)
        if len(tokens) <= max_tokens:
            return text
        return "".join(tokens[:max_tokens])


_TOKENIZER_CACHE: Dict[str, Tuple[Any, str]] = {}


class TokenBudgetManager:
    """
    Bộ quản lý ngân sách ngữ cảnh cắm-rút (Pluggable Token Budget Manager).
    """
    DEFAULT_REFERENCE_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"

    def __init__(
        self,
        tokenizer: Optional[Any] = None,
        tokenizer_name: str = DEFAULT_REFERENCE_MODEL,
        target_code_max_tokens: int = 3000,
        graph_max_tokens: int = 1500,
        demonstration_max_tokens: int = 1500,
        output_reserve_tokens: int = 64,
        context_limit: int = 8192,
        force_offline: bool = False,
    ):
        self.tokenizer_name = tokenizer_name
        self.target_code_max_tokens = target_code_max_tokens
        self.graph_max_tokens = graph_max_tokens
        self.demonstration_max_tokens = demonstration_max_tokens
        self.output_reserve_tokens = output_reserve_tokens
        self.context_limit = context_limit

        self.tokenizer_type = "offline_fallback"
        self.fallback_reason: Optional[str] = None

        if tokenizer is not None:
            self.tokenizer = tokenizer
            self.tokenizer_type = getattr(tokenizer, "__class__", type(tokenizer)).__name__
        elif force_offline:
            self.tokenizer = OfflineFallbackTokenizer()
            self.tokenizer_type = "offline_fallback"
            self.fallback_reason = "force_offline requested"
        elif tokenizer_name in _TOKENIZER_CACHE:
            self.tokenizer, self.tokenizer_type = _TOKENIZER_CACHE[tokenizer_name]
        else:
            loaded = False
            has_local = _is_model_locally_cached(tokenizer_name)
            has_net = _is_network_available()

            # Nếu không có local cache và mạng offline -> lập tức fallback, không nạp transformers
            if not has_local and not has_net:
                self.fallback_reason = "Local cache missing and HuggingFace unreachable"
            else:
                try:
                    from transformers import AutoTokenizer
                    # Thử nạp từ local cache trước để không bị trễ mạng
                    if has_local:
                        try:
                            self.tokenizer = AutoTokenizer.from_pretrained(
                                tokenizer_name,
                                trust_remote_code=False,
                                local_files_only=True,
                            )
                            self.tokenizer_type = "transformers_local"
                            _TOKENIZER_CACHE[tokenizer_name] = (self.tokenizer, self.tokenizer_type)
                            loaded = True
                        except Exception:
                            pass

                    # Nếu chưa tải được cục bộ, kiểm tra kết nối mạng trước khi gọi online download
                    if not loaded and has_net:
                        try:
                            self.tokenizer = AutoTokenizer.from_pretrained(
                                tokenizer_name,
                                trust_remote_code=False,
                                local_files_only=False,
                            )
                            self.tokenizer_type = "transformers"
                            _TOKENIZER_CACHE[tokenizer_name] = (self.tokenizer, self.tokenizer_type)
                            loaded = True
                        except Exception as exc:
                            self.fallback_reason = f"Online tokenizer load failed: {exc}"
                    elif not loaded and not self.fallback_reason:
                        self.fallback_reason = "Local cache missing and HuggingFace unreachable"
                except Exception as exc:
                    self.fallback_reason = f"Tokenizer load failed: {exc}"

            if not loaded:
                logger.info(
                    f"Sử dụng OfflineFallbackTokenizer ({self.fallback_reason})."
                )
                self.tokenizer = OfflineFallbackTokenizer()
                self.tokenizer_type = "offline_fallback"

    def count_tokens(self, text: str) -> int:
        """Đếm số lượng token trong đoạn văn bản."""
        if not text:
            return 0
        if isinstance(self.tokenizer, OfflineFallbackTokenizer):
            return self.tokenizer.count_tokens(text)
        if hasattr(self.tokenizer, "encode"):
            try:
                res = self.tokenizer.encode(text, add_special_tokens=False)
                return len(res)
            except TypeError:
                res = self.tokenizer.encode(text)
                return len(res)
        if hasattr(self.tokenizer, "tokenize"):
            return len(self.tokenizer.tokenize(text))
        # Fallback conservative heuristic
        return len(text.split())

    def truncate_text(
        self,
        text: str,
        max_tokens: int,
        suffix: str = ""
    ) -> TruncateResult:
        """
        Cắt tỉa văn bản theo token an toàn.
        Trả về TruncateResult (kế thừa tuple 4 phần tử: (truncated_text, was_truncated, original_tokens, kept_tokens)).
        """
        if not text:
            return TruncateResult("", False, 0, 0, "")

        orig_tokens = self.count_tokens(text)
        if orig_tokens <= max_tokens:
            return TruncateResult(text, False, orig_tokens, orig_tokens, text)

        suffix_tokens = self.count_tokens(suffix) if suffix else 0
        allowed_tokens = max(1, max_tokens - suffix_tokens)

        if isinstance(self.tokenizer, OfflineFallbackTokenizer):
            truncated_core = self.tokenizer.truncate(text, allowed_tokens)
        elif hasattr(self.tokenizer, "encode") and hasattr(self.tokenizer, "decode"):
            try:
                ids = self.tokenizer.encode(text, add_special_tokens=False)
            except TypeError:
                ids = self.tokenizer.encode(text)
            truncated_ids = ids[:allowed_tokens]
            truncated_core = self.tokenizer.decode(truncated_ids, skip_special_tokens=True)
        else:
            # Fallback by character ratio
            ratio = allowed_tokens / max(orig_tokens, 1)
            char_cutoff = int(len(text) * ratio)
            truncated_core = text[:char_cutoff]

        result = truncated_core + suffix if suffix else truncated_core
        kept_tokens = self.count_tokens(result)
        return TruncateResult(result, True, orig_tokens, kept_tokens, truncated_core)

    def truncate_target_code(self, code: str) -> Tuple[str, Dict[str, Any]]:
        """Cắt tỉa mã nguồn hàm mục tiêu theo ngân sách target_code_max_tokens."""
        suffix = "\n/* [TRUNCATED TARGET CODE TO PRESERVE BUDGET] */"
        res = self.truncate_text(
            code, self.target_code_max_tokens, suffix=suffix
        )
        truncated, was_truncated, orig_t, kept_t = res
        truncated_core = getattr(res, "truncated_core", code[:len(truncated)])
        stats = {
            "original_tokens": orig_t,
            "kept_tokens": kept_t,
            "was_truncated": was_truncated,
            "max_budget": self.target_code_max_tokens,
            "cut_char_index": len(truncated_core),
            "truncated_core": truncated_core,
        }
        return truncated, stats

    def truncate_demonstration(
        self,
        demo_code: str,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Cắt tỉa mã nguồn demonstration theo ngân sách demonstration_max_tokens.
        Kiểm toán cắt rỗng:
        Nếu demo bị cắt > 75% độ dài hoặc rỗng, gắn cờ truncated_demo = True.
        """
        limit = max_tokens if max_tokens is not None else self.demonstration_max_tokens
        stripped = demo_code.strip() if demo_code else ""
        if not stripped:
            return "", {
                "original_tokens": 0,
                "kept_tokens": 0,
                "core_tokens": 0,
                "was_truncated": False,
                "truncated_ratio": 1.0,
                "truncated_demo": True,
                "empty_demo": True,
                "max_budget": limit,
                "cut_char_index": 0,
                "truncated_core": "",
            }

        orig_tokens = self.count_tokens(demo_code)
        suffix = "\n/* [TRUNCATED DEMONSTRATION] */"
        res = self.truncate_text(
            demo_code, limit, suffix=suffix
        )
        truncated, was_truncated, _, kept_tokens = res
        truncated_core = getattr(res, "truncated_core", demo_code)

        core_tokens = self.count_tokens(truncated_core)
        cut_tokens = max(0, orig_tokens - core_tokens) if was_truncated else 0
        truncated_ratio = (cut_tokens / orig_tokens) if orig_tokens > 0 else 0.0

        is_empty = (core_tokens == 0 or not truncated_core.strip())
        is_severe = (truncated_ratio > 0.75) or is_empty

        stats = {
            "original_tokens": orig_tokens,
            "kept_tokens": kept_tokens,
            "core_tokens": core_tokens,
            "was_truncated": was_truncated,
            "truncated_ratio": truncated_ratio,
            "truncated_demo": is_severe,
            "empty_demo": is_empty,
            "max_budget": limit,
            "cut_char_index": len(truncated_core),
            "truncated_core": truncated_core,
        }
        return truncated, stats

    def truncate_graph(self, graph_str: str) -> Tuple[str, Dict[str, Any]]:
        """Cắt tỉa văn bản cấu trúc đồ thị CPG theo ngân sách graph_max_tokens."""
        suffix = "\n... (graph truncated to satisfy token budget)"
        res = self.truncate_text(
            graph_str, self.graph_max_tokens, suffix=suffix
        )
        truncated, was_truncated, orig_t, kept_t = res
        truncated_core = getattr(res, "truncated_core", graph_str[:len(truncated)])
        stats = {
            "original_tokens": orig_t,
            "kept_tokens": kept_t,
            "was_truncated": was_truncated,
            "max_budget": self.graph_max_tokens,
            "cut_char_index": len(truncated_core),
            "truncated_core": truncated_core,
        }
        return truncated, stats

    def audit_prompt_tokens(
        self,
        code_text: str,
        graph_text: str,
        demo_text: str,
        instruction_text: str = "",
        format_text: str = "",
    ) -> Dict[str, Any]:
        """
        Kiểm toán token toàn diện của các khối trong prompt và kiểm tra trần ngữ cảnh.
        """
        tokens_code = self.count_tokens(code_text)
        tokens_graph = self.count_tokens(graph_text)
        tokens_demo = self.count_tokens(demo_text)
        tokens_instruction = self.count_tokens(instruction_text)
        tokens_format = self.count_tokens(format_text)
        tokens_total = (
            tokens_code + tokens_graph + tokens_demo + tokens_instruction + tokens_format
        )

        total_with_reserve = tokens_total + self.output_reserve_tokens
        within_total_budget = total_with_reserve <= self.context_limit
        within_component_budgets = (
            tokens_code <= self.target_code_max_tokens + 50  # cho phép dung sai nhỏ do suffix
            and tokens_graph <= self.graph_max_tokens + 50
            and tokens_demo <= self.demonstration_max_tokens + 50
        )

        return {
            "tokens_code": tokens_code,
            "tokens_graph": tokens_graph,
            "tokens_demo": tokens_demo,
            "tokens_instruction": tokens_instruction,
            "tokens_format": tokens_format,
            "tokens_total": tokens_total,
            "output_reserve": self.output_reserve_tokens,
            "total_with_reserve": total_with_reserve,
            "context_limit": self.context_limit,
            "within_total_budget": within_total_budget,
            "within_component_budgets": within_component_budgets,
            "is_valid": within_total_budget and within_component_budgets,
        }
