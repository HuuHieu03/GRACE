"""Đếm và cắt theo token của đúng tokenizer model (đơn vị duy nhất của giao thức).

Chỉ khi không có tokenizer (chạy thử offline) mới dùng ước lượng 4 ký tự/token và
đánh dấu approx=True; kết quả approx không được dùng cho lượt chạy thật.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class FitResult:
    text: str
    tokens: int
    truncated: bool
    original_tokens: int


class TokenCounter:
    def __init__(self, model_or_path: Optional[str] = None, approx_chars_per_token: float = 4.0):
        self.model = model_or_path
        self.approx = model_or_path is None
        self.ratio = approx_chars_per_token
        self.tok = None
        if model_or_path is not None:
            from transformers import AutoTokenizer
            self.tok = AutoTokenizer.from_pretrained(model_or_path, trust_remote_code=False)

    def count(self, text: str) -> int:
        if self.tok is None:
            return int(len(text) / self.ratio + 0.999)
        return len(self.tok.encode(text, add_special_tokens=False))

    def count_chat(self, prompt: str, system: Optional[str] = None) -> int:
        """Số token thực gửi sau khi bọc chat template (để kiểm ngân sách tổng)."""
        if self.tok is None or not getattr(self.tok, "chat_template", None):
            return self.count(prompt) + 16
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        return len(self.tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True))

    def fit(self, text: str, budget: int, marker: str = "\n/* [TRUNCATED] */") -> FitResult:
        """Cắt text để số token <= budget (kể cả marker). Tìm nhị phân theo ký tự để
        không phụ thuộc vào việc decode lại token."""
        total = self.count(text)
        if total <= budget:
            return FitResult(text, total, False, total)
        marker_tokens = self.count(marker)
        target = max(1, budget - marker_tokens)
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.count(text[:mid]) <= target:
                lo = mid
            else:
                hi = mid - 1
        cut = text[:lo].rstrip() + marker
        return FitResult(cut, self.count(cut), True, total)
