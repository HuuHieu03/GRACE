"""
GRACE Resilient LLM Evaluator (Stage 3)
Module phụ trách thực hiện inference trên LLM (Hỗ trợ GPU Open-Weights trên Kaggle hoặc Mock offline),
bóc tách nhãn bằng Regex đa tần (Multi-pattern Regex Parsing),
và bảo vệ tiến trình bằng cơ chế Checkpointing JSONL tự động phục hồi khi gặp sự cố (Crash Recovery).
"""

import os
import re
import json
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from config import config
from prompt_engine import build_grace_prompt, build_prompt
from metrics import compute_classification_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_llm_prediction(response_text: str) -> Tuple[Optional[int], str, bool]:
    """
    Bóc tách chuỗi dự đoán (Multi-pattern Regex + Strict + Keyword Parsing) cho định dạng 0/1.
    Được nâng cấp để giải quyết triệt để vấn đề parser theo STEP 2 (Immediate Action Plan):
    - 'Non-vulnerable (0)', 'Label: Non-vulnerable (0)' -> 0
    - 'Vulnerable (1)', 'Label: Vulnerable (1)' -> 1
    - Phản hồi không xác định / rỗng / mâu thuẫn -> (None, desc, False) (KHÔNG ép về 0).
    
    Returns:
        (predicted_label: Optional[int], extraction_method_description: str, is_valid: bool)
    """
    if not response_text or not isinstance(response_text, str):
        return None, "Invalid: Empty Response", False
        
    text_clean = response_text.strip()
    if not text_clean:
        return None, "Invalid: Blank Whitespace", False
    
    # 1. Khớp chính xác 1 ký tự / token độc lập
    if text_clean in ["1", "'1'", '"1"', "1."]:
        return 1, "Strict '1'", True
    elif text_clean in ["0", "'0'", '"0"', "0."]:
        return 0, "Strict '0'", True
        
    # 2. Khớp dòng cuối hoặc dòng kết luận nếu toàn bộ nội dung kết thúc bằng nhãn rõ ràng
    lines = [line.strip() for line in text_clean.split("\n") if line.strip()]
    if lines:
        last_line = lines[-1].strip().lower()
        if last_line in ["1", "1.", "'1'", '"1"']:
            return 1, "Last line '1'", True
        if last_line in ["0", "0.", "'0'", '"0"']:
            return 0, "Last line '0'", True

    # 3. Kiểm tra các câu nói mâu thuẫn hoặc không xác định được (Hedging / Contradiction)
    hedging_patterns = [
        r"cannot determine",
        r"can't determine",
        r"not sure",
        r"unable to determine",
        r"both 0 and 1",
        r"both vulnerable and safe",
        r"both safe and vulnerable",
        r"vulnerable\s*\(\s*1\s*\).*safe\s*\(\s*0\s*\)",
        r"safe\s*\(\s*0\s*\).*vulnerable\s*\(\s*1\s*\)",
    ]
    if any(re.search(p, text_clean, re.IGNORECASE) for p in hedging_patterns):
        return None, "Invalid: Hedging or Contradictory Response", False

    # 4. Khớp tiền tố nhãn rõ ràng (Label: ..., Output: ..., Answer: ...)
    explicit_safe_patterns = [
        r"\bnon-vulnerable\s*\(\s*0\s*\)",
        r"\blabel:\s*non-vulnerable(?:\s*\(\s*0\s*\))?",
        r"\boutput:\s*non-vulnerable(?:\s*\(\s*0\s*\))?",
        r"\banswer:\s*non-vulnerable(?:\s*\(\s*0\s*\))?",
        r"\banswer:\s*0\b",
        r"\boutput:\s*0\b",
        r"\blabel:\s*0\b",
        r"\bprediction:\s*0\b",
    ]
    explicit_vuln_patterns = [
        r"\bvulnerable\s*\(\s*1\s*\)",
        r"\blabel:\s*vulnerable(?:\s*\(\s*1\s*\))?",
        r"\boutput:\s*vulnerable(?:\s*\(\s*1\s*\))?",
        r"\banswer:\s*vulnerable(?:\s*\(\s*1\s*\))?",
        r"\banswer:\s*1\b",
        r"\boutput:\s*1\b",
        r"\blabel:\s*1\b",
        r"\bprediction:\s*1\b",
    ]
    
    has_exp_safe = any(re.search(p, text_clean, re.IGNORECASE) for p in explicit_safe_patterns)
    has_exp_vuln = any(re.search(p, text_clean, re.IGNORECASE) for p in explicit_vuln_patterns)
    
    if has_exp_vuln and not has_exp_safe:
        return 1, "Explicit Label: Vulnerable/1", True
    if has_exp_safe and not has_exp_vuln:
        return 0, "Explicit Label: Safe/0", True
    if has_exp_vuln and has_exp_safe:
        return None, "Contradictory: Both Explicit Labels Present", False

    # 5. Regex bóc tách từ khóa ngữ nghĩa tổng quát
    # CẢNH BÁO: Phải loại trừ 'non-vulnerable' và 'not vulnerable' trước khi tìm 'vulnerable'
    safe_semantic_patterns = [
        r"\bnon-vulnerable\b",
        r"\bnot\s+vulnerable\b",
        r"\bnot\s+a\s+vulnerability\b",
        r"\bno\s+(?:security\s+)?vulnerability\b",
        r"\bfunction\s+is\s+safe\b",
        r"\bcode\s+is\s+safe\b",
        r"\bsafe\b",
    ]
    vuln_semantic_patterns = [
        r"(?<!non-)(?<!not\s)(?<!no\s)\bvulnerable\b",
        r"(?<!no\s)(?<!not\s)vulnerabilit(?:y|ies)\b",
        r"\bsecurity\s+flaw\b",
    ]
    
    is_safe = any(re.search(p, text_clean, re.IGNORECASE) for p in safe_semantic_patterns)
    is_vuln = any(re.search(p, text_clean, re.IGNORECASE) for p in vuln_semantic_patterns)
    
    if is_vuln and not is_safe:
        return 1, "Semantic Regex: Vulnerable", True
    if is_safe and not is_vuln:
        return 0, "Semantic Regex: Safe", True
    if is_vuln and is_safe:
        return None, "Contradictory: Both Vulnerable and Safe Keywords Found", False

    # 6. Fallback Heuristic chỉ khi nội dung chứa duy nhất một chữ số 0 hoặc 1 độc lập
    has_digit_1 = bool(re.search(r"\b1\b", text_clean))
    has_digit_0 = bool(re.search(r"\b0\b", text_clean))
    
    if has_digit_1 and not has_digit_0:
        return 1, "Heuristic standalone '1'", True
    if has_digit_0 and not has_digit_1:
        return 0, "Heuristic standalone '0'", True
        
    logger.warning(f"Không thể bóc tách chuẩn xác từ phản hồi LLM: '{text_clean[:100]}...'. Đánh dấu Invalid.")
    return None, "Invalid: Unparseable LLM Response", False


class CheckpointManager:
    """
    Trình quản lý lưu vết theo dòng (JSONL Checkpointing) tại `config.checkpoint_dir`.
    Giúp tiến trình chạy dài (Hàng nghìn mẫu trên Kaggle) có thể tự khôi phục sau khi crash/timeout
    mà không bao giờ mất công chạy lại từ đầu.
    
    Hỗ trợ Config Integrity Hash (SHA-256) để đảm bảo không khôi phục lẫn lộn giữa các thí nghiệm
    hoặc khi cấu hình (dataset, split, model, prompt_mode, retrieval_method, seed) bị thay đổi.
    """
    def __init__(self, experiment_name: str = "default_eval", run_config: Optional[Dict[str, Any]] = None):
        import hashlib
        self.experiment_name = experiment_name
        self.run_config = run_config or {}
        
        # Tạo SHA-256 hash từ run_config nếu có
        if self.run_config:
            # Sắp xếp key để hash bất biến
            canonical_cfg = json.dumps(self.run_config, sort_keys=True, ensure_ascii=False)
            self.config_hash = hashlib.sha256(canonical_cfg.encode("utf-8")).hexdigest()[:12]
            filename = f"checkpoint_{experiment_name}_{self.config_hash}.jsonl"
        else:
            self.config_hash = None
            filename = f"checkpoint_{experiment_name}.jsonl"

        self.checkpoint_file = config.checkpoint_dir / filename
        self.completed_ids = set()
        self.loaded_results = []
        self._load_existing_checkpoint()

    def _load_existing_checkpoint(self):
        """Đọc và khôi phục trạng thái từ tệp JSONL đã lưu (nếu tồn tại). Kiểm tra config integrity."""
        if self.checkpoint_file.exists():
            logger.info(f"Phát hiện Checkpoint cũ: {self.checkpoint_file}. Đang nạp trạng thái phục hồi...")
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Dòng đầu tiên có thể là metadata header kiểm tra toàn vẹn
                        if line_idx == 0 and record.get("_type") == "checkpoint_metadata":
                            saved_hash = record.get("config_hash")
                            if self.config_hash and saved_hash and saved_hash != self.config_hash:
                                raise RuntimeError(
                                    f"Config integrity mismatch: Checkpoint được tạo với config_hash={saved_hash}, "
                                    f"nhưng cấu hình hiện tại có hash={self.config_hash}. "
                                    f"Từ chối khôi phục để tránh làm nhiễm bẩn dữ liệu!"
                                )
                            continue

                        sample_id = record.get("id")
                        if sample_id is not None:
                            self.completed_ids.add(sample_id)
                            self.loaded_results.append(record)
                    except json.JSONDecodeError:
                        logger.warning("Phát hiện 1 dòng JSONL bị hỏng trong checkpoint. Bỏ qua dòng này.")
            logger.info(f"Đã phục hồi thành công {len(self.completed_ids)} mẫu đã hoàn thành trước đó!")
        else:
            logger.info(f"Khởi tạo phiên chạy mới. File Checkpoint mới sẽ được lưu tại: {self.checkpoint_file}")
            # Nếu có config, ghi dòng metadata header đầu tiên
            if self.run_config and not self.checkpoint_file.exists():
                meta_header = {
                    "_type": "checkpoint_metadata",
                    "experiment_name": self.experiment_name,
                    "config_hash": self.config_hash,
                    "run_config": self.run_config,
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                    f.write(json.dumps(meta_header, ensure_ascii=False) + "\n")
                    f.flush()

    def is_completed(self, sample_id: Any) -> bool:
        return sample_id in self.completed_ids

    def save_record(self, record: Dict[str, Any]):
        """Ghi lập tức 1 dòng bản ghi mới vào file checkpoint JSONL (Flush Realtime)."""
        with open(self.checkpoint_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno()) # Đảm bảo đĩa cứng thực hiện ghi liền tay
        self.completed_ids.add(record.get("id"))
        self.loaded_results.append(record)

    def clear_checkpoint(self):
        """Xóa file checkpoint (Dùng khi reset test hoặc chạy lại từ gốc)."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info(f"Đã xóa file checkpoint: {self.checkpoint_file}")
        self.completed_ids.clear()
        self.loaded_results.clear()


class LLMEvaluator:
    """
    Trình điều khiển Đánh Giá LLM (LLM Evaluation Engine).
    Hỗ trợ tích hợp Vertex AI Model-as-a-Service (MaaS) cho Qwen-3 Coder 480B
    theo evaluation_contract.yaml, OpenAI-compatible API (FPT AI Factory),
    và Intelligent Mock LLM cho kiểm thử offline tốc độ cao.
    """
    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        use_mock: bool = False,
        project_id: Optional[str] = None,
        location: Optional[str] = None
    ):
        self.use_mock = use_mock
        self.client = None
        self.credentials = None
        self.project_id = project_id or config.vertex_project_id
        self.location = location or config.vertex_location

        # Xác định Provider: Ưu tiên tham số provider, nếu không nhận diện theo model_name hoặc env
        if provider:
            self.provider = provider
        elif model_name and ("publishers/" in model_name or "qwen3" in model_name or "vertex" in model_name.lower()):
            self.provider = "Vertex AI"
        elif os.getenv("LLM_PROVIDER") == "Vertex AI":
            self.provider = "Vertex AI"
        else:
            self.provider = "FPT"

        # Xác định Model Name
        if model_name:
            self.model_name = model_name
        elif self.provider == "Vertex AI":
            self.model_name = config.vertex_model
        else:
            self.model_name = config.default_llm_model
        
        if not use_mock:
            if self.provider == "Vertex AI":
                self._init_vertex_client()
            else:
                self._init_fpt_client()
        
        if self.use_mock:
            logger.info("Môi trường Local/Test: Kích hoạt chế độ Intelligent Mock LLM Evaluator để test tốc độ cao.")

    def _init_fpt_client(self):
        """Khởi tạo OpenAI-compatible client cho FPT AI Factory."""
        api_key = config.get_api_key("FPT_API_KEY")
        base_url = config.get_base_url("FPT_BASE_URL")
        if not api_key:
            raise RuntimeError(
                "Lỗi cấu hình: Không tìm thấy FPT_API_KEY hoặc khóa API bị trống. "
                "Vui lòng cấu hình file .env hoặc biến môi trường trước khi chạy thực nghiệm. "
                "Nếu chỉ muốn kiểm thử giả lập nhanh mà không gọi API, hãy truyền flag --use_mock."
            )
        import openai
        logger.info(f"Kết nối tới API FPT: {base_url} với model {self.model_name}...")
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def _init_vertex_client(self):
        """Khởi tạo kết nối tới Vertex AI Model-as-a-Service endpoint với Service Account credentials."""
        from config import setup_vertex_credentials
        cred_path = setup_vertex_credentials()

        try:
            import google.auth
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            active_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or cred_path
            if active_cred and os.path.exists(active_cred):
                self.credentials = service_account.Credentials.from_service_account_file(
                    active_cred,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            else:
                self.credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )

            self.credentials.refresh(Request())
        except Exception as e:
            raise RuntimeError(
                f"Lỗi cấu hình: Không tìm thấy Service Account Credentials cho Vertex AI hoặc không thể xác thực: {e}. "
                "Vui lòng đảm bảo đã thiết lập Kaggle Secret 'GCP_SA_KEY' hoặc file 'grace-research-*.json' "
                "hoặc biến môi trường GOOGLE_APPLICATION_CREDENTIALS. "
                "Nếu chỉ muốn kiểm thử giả lập nhanh mà không gọi API, hãy truyền flag --use_mock."
            ) from e

        import openai
        base_url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/endpoints/openapi"
        logger.info(f"Kết nối tới Vertex AI MaaS endpoint: {base_url} với model {self.model_name}...")
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=self.credentials.token
        )

    def get_access_token(self) -> str:
        """Lấy hoặc tự động refresh OAuth2 Access Token cho Vertex AI."""
        if self.credentials is None:
            self._init_vertex_client()
        if not self.credentials.valid or self.credentials.expired:
            from google.auth.transport.requests import Request
            self.credentials.refresh(Request())
        return self.credentials.token

    def generate_response(self, prompt: str) -> str:
        """Hàm thực thi Suy nghĩ & Trả về phản hồi (Inference / Generation)."""
        if self.use_mock:
            time.sleep(0.02) # Giả lập thời gian xử lý AI
            is_risky = any(k in prompt.lower() for k in ["strcpy", "gets", "sprintf", "bad_", "vuln", "overflow", "leak"])
            pred = 1 if is_risky else 0
            return str(pred)

        if self.provider == "Vertex AI":
            # Refresh Bearer Token nếu hết hạn (thời hạn 3600s của Google OAuth2)
            token = self.get_access_token()
            self.client.api_key = token

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
                seed=42,
                stream=False
            )
            choice_msg = response.choices[0].message
            content = choice_msg.content
            if not content:
                reasoning = getattr(choice_msg, "reasoning_content", None)
                if reasoning:
                    content = reasoning
                else:
                    logger.warning("Vertex AI trả về content=None và không có reasoning_content.")
                    return ""
            return content.strip()

        # Chạy thực thi Inference trên API FPT / OpenAI-compatible
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=256,
            stream=False
        )
        choice_msg = response.choices[0].message
        content = choice_msg.content
        if not content:
            # Kiểm tra trường reasoning_content đối với các mô hình suy luận
            reasoning = getattr(choice_msg, "reasoning_content", None)
            if reasoning:
                content = reasoning
            else:
                logger.warning("FPT AI trả về content=None và không có reasoning_content.")
                return ""
        return content.strip()

    def evaluate_dataset(
        self,
        test_samples: List[Dict[str, Any]],
        experiment_name: str = "grace_run",
        include_demonstration: bool = True,
        prompt_mode: str = "standard_1shot",
        run_config: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
        min_backoff_sec: float = 5.0,
        max_backoff_sec: float = 120.0,
        request_delay: float = 0.05
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Đánh giá hàng loạt trên danh sách mẫu kiểm thử (Batch Evaluation):
        - Hỗ trợ các chế độ prompt_mode: 'zero_shot', 'standard_1shot', 'contrastive_2shot'.
        - Có kiểm tra Checkpoint cũ mang mã băm cấu hình để khôi phục tiến trình an toàn.
        - Tuân thủ nghiêm ngặt retry policy trong evaluation_contract.yaml:
          max_attempts=5; exponential_backoff=5s..120s; exhausted_request=invalid.
        - Trả về toàn bộ danh sách kết quả và ma trận đánh giá.
        """
        from tqdm import tqdm
        ckpt_manager = CheckpointManager(experiment_name=experiment_name, run_config=run_config)
        total = len(test_samples)
        logger.info(f"Bắt đầu quy trình Đánh Giá (Evaluator) cho {total} mẫu [Experiment: {experiment_name}, Mode: {prompt_mode}]...")
        
        correct_count = 0
        total_processed = 0

        # Phục hồi bộ đếm cho thanh tiến độ
        for r in ckpt_manager.loaded_results:
            if r["prediction"] == r["target"]:
                correct_count += 1
            total_processed += 1

        effective_mode = "zero_shot" if not include_demonstration else prompt_mode

        pbar = tqdm(test_samples, desc="Evaluating", unit="sample")
        for sample in pbar:
            sample_id = sample.get("id", f"sample_{total_processed}")
            
            if ckpt_manager.is_completed(sample_id):
                # Đã hoàn thành, bỏ qua
                pass
            else:
                prompt = build_prompt(sample, mode=effective_mode)
                
                llm_response = ""
                for attempt in range(1, max_retries + 1):
                    try:
                        llm_response = self.generate_response(prompt)
                        if llm_response:
                            if request_delay > 0 and not self.use_mock:
                                time.sleep(request_delay)
                            break
                        # Nếu phản hồi rỗng, chờ rồi thử lại (nếu chưa phải lần thử cuối)
                        if attempt < max_retries:
                            time.sleep(min_backoff_sec)
                        else:
                            logger.error(
                                f"Phản hồi LLM rỗng liên tục sau {max_retries} lần thử cho ID '{sample_id}'. "
                                "Đánh dấu Invalid theo evaluation_contract.yaml."
                            )
                    except Exception as e:
                        err_str = str(e)
                        wait_time = min(min_backoff_sec * (2 ** (attempt - 1)), max_backoff_sec)
                        if "429" in err_str or "rate" in err_str.lower() or "too many" in err_str.lower():
                            wait_time = max(wait_time, 20.0)
                        if attempt < max_retries:
                            logger.warning(
                                f"Lỗi Inference tại ID '{sample_id}' (Lần thử {attempt}/{max_retries}: {e}). "
                                f"Đang đợi {wait_time:.1f}s để thử lại..."
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(
                                f"Thất bại hoàn toàn sau {max_retries} lần thử (Exhausted Request) cho ID '{sample_id}': {e}. "
                                "Đánh dấu Invalid theo evaluation_contract.yaml."
                            )
                            llm_response = ""
                            
                pred_int, parse_desc, is_valid = parse_llm_prediction(llm_response)
                ground_truth = sample.get("target", 0)
                
                record = {
                    "id": sample_id,
                    "target": ground_truth,
                    "prediction": pred_int,
                    "parse_method": parse_desc,
                    "is_valid": is_valid,
                    "func_snippet": sample.get("func", "")[:120],
                    "llm_raw_response": llm_response,
                    "eval_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                ckpt_manager.save_record(record)
                
                if is_valid and ground_truth == pred_int:
                    correct_count += 1
                total_processed += 1
                
                current_acc = (correct_count / total_processed) * 100 if total_processed > 0 else 0
                
                pbar.set_description(f"Acc: {current_acc:.1f}% | ID: {str(sample_id)[:8]}")
                logger.debug(f"[{total_processed}/{total}] ID: {str(sample_id):<10} | True: {ground_truth} | Pred: {pred_int} ({'✓ PASS' if ground_truth==pred_int else '✗ FAIL'})")

        all_results = ckpt_manager.loaded_results
        y_true = [r["target"] for r in all_results]
        y_pred = [r["prediction"] for r in all_results]
        
        metrics = compute_classification_metrics(y_true, y_pred)
        return all_results, metrics
