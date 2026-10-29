"""Gọi LLM tự host (vLLM hoặc llama.cpp, OpenAI-compatible) và lấy điểm số liên tục
từ logprob của token đầu tiên.

Điểm số s = p("1") / (p("0") + p("1")). Nhãn argmax = 1 nếu p1 >= p0.
Một phản hồi là hợp lệ khi ít nhất một trong hai token "0"/"1" nằm trong top-k logprob
của token đầu tiên; nếu không, ghi invalid và giữ nguyên raw để báo cáo.

Cache: mỗi kết quả được ghi vào một file JSON đặt tên theo khóa
sha256(prompt | model | tham số suy luận | parser_version), nên đổi model/tham số
sẽ không bao giờ dùng nhầm phản hồi cũ.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

PARSER_VERSION = "logprob_binary_v1"
DIGIT_ALIASES = {"0": "0", "1": "1", " 0": "0", " 1": "1", "0\n": "0", "1\n": "1"}


@dataclass
class BackendConfig:
    kind: str = "vllm"                      # "vllm" | "llamacpp"
    base_url: str = "http://localhost:8000/v1"
    model: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    api_key: str = "EMPTY"
    temperature: float = 0.0
    max_tokens: int = 1
    top_logprobs: int = 5
    seed: int = 42
    guided_choice: bool = False             # bật khi smoke test cho thấy < 99% prompt có token 0/1 trong top-k
    timeout_s: float = 120.0
    system_prompt: Optional[str] = None     # None = chỉ một message role=user (giống mã tác giả)

    def inference_identity(self) -> Dict[str, Any]:
        return {"kind": self.kind, "model": self.model, "temperature": self.temperature,
                "max_tokens": self.max_tokens, "top_logprobs": self.top_logprobs,
                "seed": self.seed, "guided_choice": self.guided_choice,
                "system_prompt": self.system_prompt, "parser_version": PARSER_VERSION}


@dataclass
class ScoreResult:
    s: float
    p0: float
    p1: float
    pred_argmax: Optional[int]
    valid: bool
    raw: str
    top: Dict[str, float]
    usage: Optional[Dict[str, Any]]
    latency_s: float
    cached: bool = False
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)


def request_key(prompt: str, cfg: BackendConfig) -> str:
    payload = json.dumps({"prompt": prompt, **cfg.inference_identity()}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_top_logprobs(top: Dict[str, float]) -> Dict[str, Any]:
    """Từ dict token -> logprob của token đầu tiên, tính p0, p1, s, nhãn và cờ hợp lệ.

    Token có thể kèm khoảng trắng/xuống dòng tùy tokenizer; gộp các biến thể về "0"/"1".
    Nếu cả hai vắng mặt trong top-k thì invalid (không ép về 0).
    """
    lp = {"0": None, "1": None}
    for tok, val in top.items():
        key = DIGIT_ALIASES.get(tok)
        if key is None:
            key = DIGIT_ALIASES.get(tok.strip())
        if key is not None and (lp[key] is None or val > lp[key]):
            lp[key] = float(val)
    valid = lp["0"] is not None or lp["1"] is not None
    p0 = math.exp(lp["0"]) if lp["0"] is not None else 0.0
    p1 = math.exp(lp["1"]) if lp["1"] is not None else 0.0
    if not valid:
        return {"s": float("nan"), "p0": 0.0, "p1": 0.0, "pred_argmax": None, "valid": False}
    s = p1 / (p0 + p1)
    return {"s": s, "p0": p0, "p1": p1, "pred_argmax": int(p1 >= p0), "valid": True}


class FirstTokenScorer:
    """Client mỏng trên SDK openai; dùng được với vLLM và llama.cpp server."""

    def __init__(self, cfg: BackendConfig, cache_dir: Optional[Path] = None):
        from openai import OpenAI  # import muộn để test không cần SDK
        self.cfg = cfg
        self.client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, max_retries=0, timeout=cfg.timeout_s)
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- payload -----------------------------------------------------------
    def build_payload(self, prompt: str) -> Dict[str, Any]:
        messages = []
        if self.cfg.system_prompt:
            messages.append({"role": "system", "content": self.cfg.system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {
            "model": self.cfg.model, "messages": messages,
            "temperature": self.cfg.temperature, "max_tokens": self.cfg.max_tokens,
            "logprobs": True, "top_logprobs": self.cfg.top_logprobs, "seed": self.cfg.seed,
        }
        if self.cfg.guided_choice:
            if self.cfg.kind == "vllm":
                payload["extra_body"] = {"guided_choice": ["0", "1"]}
            else:  # llama.cpp: GBNF grammar
                payload["extra_body"] = {"grammar": 'root ::= "0" | "1"'}
        return payload

    # -- cache -------------------------------------------------------------
    def _cache_path(self, key: str) -> Optional[Path]:
        return self.cache_dir / f"{key}.json" if self.cache_dir else None

    def _read_cache(self, key: str) -> Optional[ScoreResult]:
        path = self._cache_path(key)
        if path and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            data["cached"] = True
            return ScoreResult(**data)
        return None

    def _write_cache(self, key: str, result: ScoreResult) -> None:
        path = self._cache_path(key)
        if path:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(result.to_dict(), ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)

    # -- scoring -----------------------------------------------------------
    def score(self, prompt: str, use_cache: bool = True) -> ScoreResult:
        key = request_key(prompt, self.cfg)
        if use_cache:
            hit = self._read_cache(key)
            if hit is not None:
                return hit
        payload = self.build_payload(prompt)
        t0 = time.time()
        try:
            resp = self.client.chat.completions.create(**payload)
        except Exception as exc:  # lỗi mạng/server: trả invalid kèm thông báo, không retry ngầm
            return ScoreResult(float("nan"), 0.0, 0.0, None, False, "", {}, None, time.time() - t0, False, type(exc).__name__ + ": " + str(exc)[:200])
        latency = time.time() - t0
        result = self.parse_response(resp, latency)
        if result.error is None:
            self._write_cache(key, result)
        return result

    @staticmethod
    def parse_response(resp: Any, latency: float = 0.0) -> ScoreResult:
        choice = resp.choices[0]
        raw = choice.message.content or ""
        top: Dict[str, float] = {}
        lp = getattr(choice, "logprobs", None)
        content = getattr(lp, "content", None) if lp is not None else None
        if content:
            first = content[0]
            for t in getattr(first, "top_logprobs", []) or []:
                top[t.token] = float(t.logprob)
            # một số server chỉ trả token được chọn mà không có top_logprobs
            if not top and getattr(first, "token", None) is not None:
                top[first.token] = float(first.logprob)
        parsed = parse_top_logprobs(top) if top else {"s": float("nan"), "p0": 0.0, "p1": 0.0, "pred_argmax": None, "valid": False}
        usage = None
        if getattr(resp, "usage", None) is not None:
            u = resp.usage
            usage = {"prompt_tokens": getattr(u, "prompt_tokens", None), "completion_tokens": getattr(u, "completion_tokens", None)}
        err = None if top else "no_logprobs_in_response"
        return ScoreResult(parsed["s"], parsed["p0"], parsed["p1"], parsed["pred_argmax"], parsed["valid"], raw, top, usage, latency, False, err)


def load_backend_config(path: Path) -> BackendConfig:
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return BackendConfig(**data["backend"])
