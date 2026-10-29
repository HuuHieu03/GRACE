#!/usr/bin/env python3
"""Kaggle LLM Host Runner & Plug-in Manager.

Tiện ích quản lý, cắm-rút và khởi chạy server LLM mã nguồn mở trên Kaggle GPU (0 USD).
Đọc cấu hình từ `configs/kaggle_model_registry.yaml`, hỗ trợ:
- Kiểm tra phần cứng GPU (2x Tesla T4 16GB, 1x Tesla P100 16GB).
- Tải mô hình tự động từ Hugging Face Hub (GGUF, AWQ, FP8, bfloat16).
- Sinh lệnh khởi chạy chuẩn OpenAI-compatible cho các engine: llama.cpp / llama-server, vLLM, Transformers.
- Kiểm thử tại chỗ (Smoke Test) với `logprobs=True, top_logprobs=5` để tương thích 100% với
  `smoke_test_backend.py` và `run_matrix.py` của Thầy.
- Tự động xuất file cấu hình backend YAML cho `grace_diag_kit`.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import yaml


def find_registry_config(custom_path: Optional[Path] = None) -> Path:
    """Tìm file cấu hình registry."""
    if custom_path and custom_path.exists():
        return custom_path
    
    candidates = [
        Path("configs/kaggle_model_registry.yaml"),
        Path(__file__).resolve().parents[1] / "configs" / "kaggle_model_registry.yaml",
        Path("kaggle_model_registry.yaml"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Không tìm thấy tệp cấu hình configs/kaggle_model_registry.yaml!")


def load_registry(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def inspect_hardware() -> Dict[str, Any]:
    """Phát hiện và đánh giá phần cứng GPU khả dụng."""
    info: Dict[str, Any] = {
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
        "total_vram_gb": 0.0,
        "detected_profile": "cpu_only",
    }
    try:
        import torch
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["device_count"] = torch.cuda.device_count()
            total_vram = 0.0
            for i in range(info["device_count"]):
                name = torch.cuda.get_device_name(i)
                mem = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)
                total_vram += mem
                info["devices"].append({"index": i, "name": name, "vram_gb": round(mem, 2)})
            info["total_vram_gb"] = round(total_vram, 2)

            # Phân loại profile
            if info["device_count"] >= 2 and any("T4" in d["name"] for d in info["devices"]):
                info["detected_profile"] = "kaggle_2xt4"
            elif info["device_count"] >= 1 and any("P100" in d["name"] for d in info["devices"]):
                info["detected_profile"] = "kaggle_1xp100"
            elif info["device_count"] >= 2:
                info["detected_profile"] = "multi_gpu_custom"
            else:
                info["detected_profile"] = "single_gpu_custom"
    except ImportError:
        pass

    return info


def list_registered_models(registry: Dict[str, Any]):
    """Hiển thị danh sách các model và engine có trong registry."""
    print("\n" + "=" * 78)
    print("       DANH MỤC PLUG-IN MODEL TRONG REGISTRY KAGGLE LLM HOST")
    print("=" * 78)
    models = registry.get("models", {})
    for mid, mdata in models.items():
        print(f"\n📦 [{mid}] : {mdata.get('display_name')} ({mdata.get('parameters')})")
        print(f"   - HF Repo:   {mdata.get('hf_repo')}")
        if mdata.get("gguf_file"):
            print(f"   - GGUF File: {mdata.get('gguf_file')}")
        print(f"   - Hardware:  {', '.join(mdata.get('recommended_hardware', []))}")
        print("   - Engines hỗ trợ:")
        for eng, edata in mdata.get("engines", {}).items():
            if edata.get("supported"):
                vram = edata.get("vram_required_gb", "N/A")
                fmt = edata.get("weight_format", "N/A")
                print(f"       * {eng:<12} [Format: {fmt:<8} | VRAM: ~{vram} GB]")
    print("\n" + "=" * 78)


def build_server_command(
    registry: Dict[str, Any],
    model_id: str,
    engine: str,
    model_path_or_repo: str,
    port: int = 8080,
    host: str = "0.0.0.0",
) -> List[str]:
    """Sinh danh sách tham số dòng lệnh khởi chạy server tương ứng."""
    model_cfg = registry.get("models", {}).get(model_id)
    if not model_cfg:
        raise ValueError(f"Model ID '{model_id}' không tồn tại trong registry!")

    engine_cfg = model_cfg.get("engines", {}).get(engine)
    if not engine_cfg or not engine_cfg.get("supported"):
        raise ValueError(f"Engine '{engine}' không được hỗ trợ cho model '{model_id}'!")

    cmd = []
    if engine == "llamacpp":
        server_bin = engine_cfg.get("server_binary", "llama-server")
        if shutil.which(server_bin) is None:
            # Fallback module python
            cmd = [sys.executable, "-m", engine_cfg.get("python_module", "llama_cpp.server")]
            cmd.extend(["--model", str(model_path_or_repo)])
            cmd.extend(["--host", host, "--port", str(port)])
        else:
            cmd = [server_bin, "-m", str(model_path_or_repo)]
            cmd.extend(["--host", host, "--port", str(port)])

        # Thêm cờ CLI từ cấu hình
        cmd.extend(engine_cfg.get("cli_args", []))

    elif engine == "vllm":
        cmd = ["vllm", "serve", str(model_path_or_repo)]
        cmd.extend(["--host", host, "--port", str(port)])
        tp = engine_cfg.get("tensor_parallel_size", 1)
        if tp > 1 and "--tensor-parallel-size" not in engine_cfg.get("cli_args", []):
            cmd.extend(["--tensor-parallel-size", str(tp)])
        cmd.extend(engine_cfg.get("cli_args", []))

    elif engine == "transformers":
        # Runner script transformers server
        cmd = [
            sys.executable,
            "-m",
            "scripts.kaggle_host_runner",
            "--serve-transformers",
            "--model",
            str(model_path_or_repo),
            "--host",
            host,
            "--port",
            str(port),
        ]
    else:
        raise ValueError(f"Chưa hỗ trợ sinh lệnh cho engine: {engine}")

    return cmd


def download_model_weights(
    registry: Dict[str, Any],
    model_id: str,
    engine: str,
    target_dir: Path = Path("models"),
    dry_run: bool = False,
) -> str:
    """Tải trọng số mô hình từ Hugging Face Hub (hỗ trợ GGUF, AWQ hoặc HF repo)."""
    model_cfg = registry.get("models", {}).get(model_id)
    if not model_cfg:
        raise ValueError(f"Model ID '{model_id}' không tồn tại trong registry!")

    target_dir.mkdir(parents=True, exist_ok=True)

    if engine == "llamacpp":
        gguf_repo = model_cfg.get("gguf_repo")
        gguf_file = model_cfg.get("gguf_file")
        if not gguf_repo or not gguf_file:
            raise ValueError(f"Model '{model_id}' thiếu cấu hình gguf_repo/gguf_file!")

        local_path = target_dir / gguf_file
        if local_path.exists():
            print(f"[*] File GGUF đã tồn tại tại: {local_path} ({local_path.stat().st_size / (1024**3):.2f} GB)")
            return str(local_path)

        if dry_run:
            print(f"[*] [Dry-Run] Dự kiến sử dụng file GGUF: {local_path} (từ {gguf_repo}/{gguf_file})")
            return str(local_path)

        print(f"[*] Đang tải GGUF từ Hugging Face: {gguf_repo}/{gguf_file}...")
        try:
            from huggingface_hub import hf_hub_download
            downloaded = hf_hub_download(
                repo_id=gguf_repo,
                filename=gguf_file,
                local_dir=str(target_dir),
            )
            print(f"[OK] Đã tải xong GGUF: {downloaded}")
            return downloaded
        except Exception as exc:
            print(f"[!] Không thể tự động tải qua huggingface_hub ({exc}).")
            hf_url = f"https://huggingface.co/{gguf_repo}/resolve/main/{gguf_file}"
            print(f"[*] Hướng dẫn tải thủ công bằng wget / curl:")
            print(f"    wget -c \"{hf_url}\" -O \"{local_path}\"")
            return str(local_path)

    elif engine == "vllm":
        awq_repo = model_cfg.get("awq_repo")
        if awq_repo:
            return awq_repo
        return model_cfg.get("hf_repo")

    else:
        return model_cfg.get("hf_repo")


def export_backend_yaml(
    output_path: Path,
    base_url: str,
    model_alias: str,
    kind: str = "llamacpp",
    top_logprobs: int = 5,
    timeout_s: float = 180.0,
):
    """Xuất file backend YAML tương thích với grace_diag_kit."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "backend": {
            "kind": kind,
            "base_url": base_url,
            "model": model_alias,
            "api_key": "EMPTY",
            "temperature": 0.0,
            "max_tokens": 1,
            "top_logprobs": top_logprobs,
            "seed": 42,
            "guided_choice": False,
            "timeout_s": timeout_s,
            "system_prompt": None,
        }
    }
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"[*] Đã xuất cấu hình backend GRACE tương thích: {output_path}")


def test_endpoint_smoke(
    base_url: str,
    model_name: str,
    test_prompt: str = "Is the following C function vulnerable to buffer overflow? Answer only 0 or 1.\nint vuln() { char b[4]; strcpy(b, \"123456\"); }",
    top_logprobs: int = 5,
) -> Dict[str, Any]:
    """Kiểm thử tính tương thích của OpenAI endpoint và kiểm tra top_logprobs."""
    import urllib.request
    import urllib.error

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": test_prompt}],
        "temperature": 0.0,
        "max_tokens": 1,
        "logprobs": True,
        "top_logprobs": top_logprobs,
        "seed": 42,
    }

    print(f"[*] Đang gửi yêu cầu smoke test tới: {url}...")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer EMPTY"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            latency = time.time() - t0
            status_code = resp.status
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except urllib.error.URLError as e:
        print(f"[!] Lỗi kết nối tới endpoint: {e}")
        return {"pass": False, "error": str(e), "latency_s": time.time() - t0}

    # Phân tích phản hồi logprobs
    choices = data.get("choices", [])
    if not choices:
        return {"pass": False, "error": "Không có choices trong response", "raw": data}

    choice = choices[0]
    logprobs_obj = choice.get("logprobs")
    if not logprobs_obj or not logprobs_obj.get("content"):
        return {"pass": False, "error": "Không tìm thấy logprobs.content trong response", "raw": data}

    first_token_lp = logprobs_obj["content"][0]
    top_items = first_token_lp.get("top_logprobs", [])

    token_map = {}
    for item in top_items:
        token_map[item.get("token", "").strip()] = item.get("logprob")

    has_zero = "0" in token_map
    has_one = "1" in token_map
    valid_binary = has_zero or has_one

    p0 = math.exp(token_map["0"]) if has_zero else 0.0
    p1 = math.exp(token_map["1"]) if has_one else 0.0
    s_score = p1 / (p0 + p1) if (p0 + p1) > 0 else float("nan")

    result = {
        "pass": valid_binary,
        "status_code": status_code,
        "latency_s": round(latency, 3),
        "raw_response": choice.get("message", {}).get("content"),
        "has_token_0": has_zero,
        "has_token_1": has_one,
        "p0": round(p0, 4),
        "p1": round(p1, 4),
        "s_score": round(s_score, 4) if not math.isnan(s_score) else None,
        "top_logprobs": token_map,
    }

    print("\n" + "-" * 60)
    print("           KẾT QUẢ KIỂM THỬ ENDPOINT (SMOKE TEST)")
    print("-" * 60)
    print(f"  Trạng thái HTTP:     {status_code} OK (Độ trễ: {latency:.3f}s)")
    print(f"  Token đầu tiên:      '{choice.get('message', {}).get('content')}'")
    print(f"  Top Logprobs nhận:   {list(token_map.keys())}")
    print(f"  Chứa token '0':      {has_zero} (p0 = {p0:.4f})")
    print(f"  Chứa token '1':      {has_one} (p1 = {p1:.4f})")
    print(f"  Điểm liên tục s:     {result['s_score']}")
    print(f"  Kết luận tiêu chí:   {'✅ ĐẠT YÊU CẦU' if valid_binary else '❌ CHƯA ĐẠT (Thiếu token 0/1 trong top_logprobs)'}")
    print("-" * 60 + "\n")

    return result


def run_transformers_server(model_name_or_path: str, host: str = "0.0.0.0", port: int = 8080):
    """Máy chủ OpenAI-compatible siêu nhẹ dùng HuggingFace Transformers (hỗ trợ logprobs)."""
    import http.server
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[*] Đang tải mô hình Transformers: {model_name_or_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, trust_remote_code=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_name_or_path,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True,
    )
    model.eval()
    print(f"[OK] Đã tải xong mô hình lên {device}. Bắt đầu lắng nghe tại http://{host}:{port}...")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/health", "/v1/health"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path.rstrip("/") in ("/v1/chat/completions", "/chat/completions"):
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                try:
                    req_data = json.loads(post_body)
                except Exception as e:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                    return

                messages = req_data.get("messages", [])
                top_logprobs_k = int(req_data.get("top_logprobs", 5))

                if hasattr(tokenizer, "apply_chat_template"):
                    prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                else:
                    prompt_text = "\n".join(m.get("content", "") for m in messages)

                inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
                with torch.no_grad():
                    outputs = model(**inputs)
                    next_token_logits = outputs.logits[:, -1, :]
                    log_probs = torch.log_softmax(next_token_logits, dim=-1)
                    topk_logprobs, topk_indices = torch.topk(log_probs, k=top_logprobs_k, dim=-1)

                top_lp_list = []
                for lp, idx in zip(topk_logprobs[0].tolist(), topk_indices[0].tolist()):
                    token_str = tokenizer.decode([idx])
                    top_lp_list.append({"token": token_str, "logprob": float(lp)})

                best_token_id = topk_indices[0, 0].item()
                best_token_str = tokenizer.decode([best_token_id])

                response_payload = {
                    "id": "chatcmpl-transformers",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": req_data.get("model", model_name_or_path),
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": best_token_str},
                            "finish_reason": "length",
                            "logprobs": {
                                "content": [
                                    {
                                        "token": best_token_str,
                                        "logprob": topk_logprobs[0, 0].item(),
                                        "top_logprobs": top_lp_list,
                                    }
                                ]
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": inputs["input_ids"].shape[1],
                        "completion_tokens": 1,
                        "total_tokens": inputs["input_ids"].shape[1] + 1,
                    },
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            return

    server = http.server.HTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Dừng server Transformers.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="Kaggle LLM Host Runner & Modular Registry Manager"
    )
    parser.add_argument("--registry", type=Path, default=None, help="Đường dẫn file cấu hình registry YAML")
    parser.add_argument("--list-models", action="store_true", help="Hiển thị danh sách model có trong registry")
    parser.add_argument("--inspect-gpu", action="store_true", help="Phát hiện và hiển thị phần cứng GPU hiện tại")
    parser.add_argument("--model", type=str, default="qwen2.5-coder-7b-instruct", help="Model ID cần sử dụng")
    parser.add_argument("--engine", type=str, default="llamacpp", choices=["llamacpp", "vllm", "transformers"], help="Inference engine")
    parser.add_argument("--port", type=int, default=8080, help="Cổng server API (mặc định 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Địa chỉ bind (mặc định 0.0.0.0)")
    parser.add_argument("--dry-run", action="store_true", help="In lệnh khởi chạy và cấu hình backend mà không chạy server")
    parser.add_argument("--download-only", action="store_true", help="Chỉ tải trọng số mô hình về máy")
    parser.add_argument("--test-endpoint", type=str, default=None, help="Kiểm thử endpoint OpenAI đang hoạt động (ví dụ: http://localhost:8080/v1)")
    parser.add_argument("--export-backend", type=Path, default=None, help="Xuất file cấu hình backend YAML cho grace_diag_kit")
    parser.add_argument("--serve-transformers", action="store_true", help="Chế độ chạy server Transformers nội bộ")

    args = parser.parse_args()

    if args.serve_transformers:
        run_transformers_server(args.model, host=args.host, port=args.port)
        return

    reg_path = find_registry_config(args.registry)
    registry = load_registry(reg_path)

    if args.list_models:
        list_registered_models(registry)
        return

    if args.inspect_gpu:
        hw = inspect_hardware()
        print("\n" + "=" * 60)
        print("          KẾT QUẢ PHÁT HIỆN PHẦN CỨNG GPU")
        print("=" * 60)
        print(f"  CUDA Khả dụng:       {hw['cuda_available']}")
        print(f"  Số lượng GPU:        {hw['device_count']}")
        print(f"  Tổng dung lượng VRAM: {hw['total_vram_gb']} GB")
        print(f"  Profile nhận diện:   {hw['detected_profile']}")
        for d in hw["devices"]:
            print(f"    - GPU [{d['index']}]: {d['name']} ({d['vram_gb']} GB VRAM)")
        print("=" * 60 + "\n")
        return

    if args.test_endpoint:
        test_endpoint_smoke(base_url=args.test_endpoint, model_name=args.model)
        return

    model_id = args.model
    engine = args.engine
    model_cfg = registry.get("models", {}).get(model_id)
    if not model_cfg:
        print(f"[!] Lỗi: Model '{model_id}' không tồn tại trong registry.")
        list_registered_models(registry)
        sys.exit(1)

    print(f"[*] Khởi tạo runner: Model = {model_id} | Engine = {engine}")
    
    # Kiểm tra phần cứng
    hw = inspect_hardware()
    if hw["cuda_available"]:
        print(f"[*] Phát hiện GPU: {hw['device_count']}x {hw['devices'][0]['name']} (Tổng {hw['total_vram_gb']} GB VRAM)")
    else:
        print("[!] Cảnh báo: Không phát hiện CUDA GPU. Server có thể chạy ở chế độ CPU (chậm).")

    # Xác định đường dẫn trọng số
    model_weight_path = download_model_weights(registry, model_id, engine, dry_run=args.dry_run)

    if args.download_only:
        print(f"[OK] Hoàn tất quá trình tải trọng số cho '{model_id}'.")
        return

    # Sinh lệnh khởi chạy
    cmd = build_server_command(registry, model_id, engine, model_weight_path, port=args.port, host=args.host)
    cmd_str = " ".join(cmd)
    print("\n" + "=" * 70)
    print("                 LỆNH KHỞI CHẠY SERVER TƯƠNG ỨNG")
    print("=" * 70)
    print(f"  {cmd_str}")
    print("=" * 70 + "\n")

    # Xuất cấu hình backend nếu có yêu cầu
    if args.export_backend:
        alias = model_cfg.get("engines", {}).get(engine, {}).get("alias", model_id)
        export_backend_yaml(
            output_path=args.export_backend,
            base_url=f"http://127.0.0.1:{args.port}/v1",
            model_alias=alias,
            kind="llamacpp" if engine == "llamacpp" else "vllm",
        )

    if args.dry_run:
        print("[*] Chế độ Dry-Run: Đã kiểm tra cấu hình thành công, không kích hoạt tiến trình nền.")
        return

    # Khởi chạy server nền
    print(f"[*] Đang khởi động server tiến trình nền...")
    proc = subprocess.Popen(cmd)
    try:
        print(f"[*] Server đang chạy với PID: {proc.pid}")
        print(f"[*] Đang chờ 5s để server khởi động sơ bộ...")
        time.sleep(5)
        test_endpoint_smoke(f"http://127.0.0.1:{args.port}/v1", model_id)
        proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Đang dừng server theo yêu cầu người dùng...")
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
