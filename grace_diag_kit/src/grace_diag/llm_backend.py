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

    max_attempts: int = 5                   # Số lần retry tối đa khi gặp lỗi mạng/timeout (tuân thủ evaluation_contract.yaml)

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


def request_key(prompt: str, cfg: BackendConfig, seed: Optional[int] = None) -> str:
    ident = cfg.inference_identity()
    if seed is not None:
        ident["seed"] = seed
    payload = json.dumps({"prompt": prompt, **ident}, sort_keys=True, ensure_ascii=False)
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
        self.cfg = cfg
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        if cfg.kind == "mock":
            self.client = None
        else:
            from openai import OpenAI  # import muộn để test không cần SDK
            try:
                import httpx
                # Tái sử dụng connection pool qua HTTP keep-alive để giảm overhead bắt tay TCP
                limits = httpx.Limits(max_keepalive_connections=50, max_connections=100, keepalive_expiry=120.0)
                http_client = httpx.Client(limits=limits, timeout=cfg.timeout_s)
                self.client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, max_retries=0, timeout=cfg.timeout_s, http_client=http_client)
            except Exception:
                self.client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, max_retries=0, timeout=cfg.timeout_s)

    # -- payload -----------------------------------------------------------
    def build_payload(self, prompt: str, seed: Optional[int] = None) -> Dict[str, Any]:
        eff_seed = seed if seed is not None else self.cfg.seed
        messages = []
        if self.cfg.system_prompt:
            messages.append({"role": "system", "content": self.cfg.system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {
            "model": self.cfg.model, "messages": messages,
            "temperature": self.cfg.temperature, "max_tokens": self.cfg.max_tokens,
            "logprobs": True, "top_logprobs": self.cfg.top_logprobs, "seed": eff_seed,
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
    def score(self, prompt: str, use_cache: bool = True, seed: Optional[int] = None) -> ScoreResult:
        eff_seed = seed if seed is not None else self.cfg.seed
        key = request_key(prompt, self.cfg, seed=eff_seed)
        if use_cache:
            hit = self._read_cache(key)
            if hit is not None:
                return hit
        t0 = time.time()
        if self.cfg.kind == "mock":
            h_hex = hashlib.sha256((prompt + str(eff_seed)).encode("utf-8")).hexdigest()
            h_int = int(h_hex[:12], 16)
            raw_s = 0.05 + 0.90 * ((h_int % 10000) / 10000.0)
            p1 = float(raw_s)
            p0 = float(1.0 - raw_s)
            pred_argmax = int(p1 >= p0)
            raw = str(pred_argmax)
            top = {"0": math.log(max(p0, 1e-6)), "1": math.log(max(p1, 1e-6))}
            latency = max(0.001, time.time() - t0)
            usage = {"prompt_tokens": len(prompt.split()), "completion_tokens": 1}
            result = ScoreResult(s=raw_s, p0=p0, p1=p1, pred_argmax=pred_argmax, valid=True,
                                 raw=raw, top=top, usage=usage, latency_s=latency, cached=False, error=None)
            self._write_cache(key, result)
            return result
        payload = self.build_payload(prompt, seed=eff_seed)
        max_attempts = getattr(self.cfg, "max_attempts", 5)
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                resp = self.client.chat.completions.create(**payload)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                # Kiểm tra lỗi client không thể thử lại (HTTP 400 Bad Request, context length exceeded, etc.)
                status_code = getattr(exc, "status_code", None)
                exc_str = str(exc).lower()
                is_non_retryable = (
                    status_code in (400, 401, 403, 404, 422)
                    or "badrequesterror" in type(exc).__name__.lower()
                    or "context length" in exc_str
                    or "maximum context" in exc_str
                    or "too many tokens" in exc_str
                    or "prompt length" in exc_str
                )
                if is_non_retryable:
                    # Fail fast: Lỗi vượt quá context hoặc 400 Bad Request là lỗi tất định, không thử lại
                    break
                if attempt < max_attempts:
                    backoff = min(120.0, 5.0 * (2 ** (attempt - 1)))
                    time.sleep(backoff)
        if last_exc is not None:
            return ScoreResult(float("nan"), 0.0, 0.0, None, False, "", {}, None, time.time() - t0, False, type(last_exc).__name__ + ": " + str(last_exc)[:200])
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
    import dataclasses
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    raw = data.get("backend", {})
    field_names = {f.name for f in dataclasses.fields(BackendConfig)}
    filtered = {k: v for k, v in raw.items() if k in field_names}
    return BackendConfig(**filtered)
