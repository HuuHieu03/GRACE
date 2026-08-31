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
from prompt_engine import build_grace_prompt
from metrics import compute_classification_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_llm_prediction(response_text: str) -> Tuple[int, str]:
    """
    Bóc tách chuỗi dự đoán (Multi-pattern Regex + Strict + Keyword Parsing) cho định dạng 0/1.
    Returns: (predicted_label_int, extraction_method_description)
    """
    if not response_text or not isinstance(response_text, str):
        return 0, "Fallback: Empty Response"
        
    text_clean = response_text.strip()
    
    # 1. Khớp chính xác 1 ký tự
    if text_clean == "1":
        return 1, "Strict '1'"
    elif text_clean == "0":
        return 0, "Strict '0'"
        
    # 2. Khớp dòng cuối hoặc từ khóa kết luận
    lines = [line.strip() for line in text_clean.split("\n") if line.strip()]
    if lines:
        last_line = lines[-1]
        if last_line in ["1", "1.", "'1'", '"1"']:
            return 1, "Last line '1'"
        if last_line in ["0", "0.", "'0'", '"0"']:
            return 0, "Last line '0'"
            
    # 3. Regex bóc tách từ khóa kết luận
    vuln_patterns = [r"\bvulnerable\b", r"\bcontains? (?:a )?vulnerability\b", r"\bsecurity flaw\b", r"\banswer:\s*1\b", r"\boutput:\s*1\b"]
    safe_patterns = [r"\bsafe\b", r"\bnot vulnerable\b", r"\bno (?:security )?vulnerability\b", r"\banswer:\s*0\b", r"\boutput:\s*0\b"]
    
    is_vuln = any(re.search(p, text_clean, re.IGNORECASE) for p in vuln_patterns)
    is_safe = any(re.search(p, text_clean, re.IGNORECASE) for p in safe_patterns)
    
    if is_vuln and not is_safe:
        return 1, "Keyword/Regex: Vulnerable"
    if is_safe and not is_vuln:
        return 0, "Keyword/Regex: Safe"
        
    # 4. Heuristic fallback nếu chỉ chứa 1 trong 2 số
    if "1" in text_clean and "0" not in text_clean:
        return 1, "Heuristic contains '1'"
    if "0" in text_clean and "1" not in text_clean:
        return 0, "Heuristic contains '0'"
        
    logger.warning(f"Không thể bóc tách chuẩn xác từ LLM: '{text_clean[:100]}...'. Áp dụng Default Fallback = 0 (Safe).")
    return 0, "Fallback: Safe/0 by default"


class CheckpointManager:
    """
    Trình quản lý lưu vết theo dòng (JSONL Checkpointing) tại `config.checkpoint_dir`.
    Giúp tiến trình chạy dài (Hàng nghìn mẫu trên Kaggle) có thể tự khôi phục sau khi crash/timeout
    mà không bao giờ mất công chạy lại từ đầu.
    """
    def __init__(self, experiment_name: str = "default_eval"):
        self.experiment_name = experiment_name
        self.checkpoint_file = config.checkpoint_dir / f"checkpoint_{experiment_name}.jsonl"
        self.completed_ids = set()
        self.loaded_results = []
        self._load_existing_checkpoint()

    def _load_existing_checkpoint(self):
        """Đọc và khôi phục trạng thái từ tệp JSONL đã lưu (nếu tồn tại)."""
        if self.checkpoint_file.exists():
            logger.info(f"Phát hiện Checkpoint cũ: {self.checkpoint_file}. Đang nạp trạng thái phục hồi...")
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            sample_id = record.get("id")
                            if sample_id is not None:
                                self.completed_ids.add(sample_id)
                                self.loaded_results.append(record)
                        except json.JSONDecodeError:
                            logger.warning("Phát hiện 1 dòng JSONL bị hỏng trong checkpoint. Bỏ qua dòng này.")
            logger.info(f"Đã phục hồi thành công {len(self.completed_ids)} mẫu đã hoàn thành trước đó!")
        else:
            logger.info(f"Khởi tạo phiên chạy mới. File Checkpoint mới sẽ được lưu tại: {self.checkpoint_file}")

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
    Hỗ trợ tích hợp Open-Weights trên Kaggle GPU và Mock Intelligent Generator cho chạy thử cục bộ.
    """
    def __init__(self, model_name: Optional[str] = None, use_mock: bool = False):
        self.model_name = model_name if model_name else config.default_llm_model
        self.use_mock = use_mock
        self.client = None
        
        if not use_mock:
            api_key = config.get_api_key("FPT_API_KEY")
            base_url = config.get_base_url("FPT_BASE_URL")
            if not api_key:
                logger.warning("Không tìm thấy API Key. Chuyển sang Mock Mode.")
                self.use_mock = True
            else:
                import openai
                logger.info(f"Kết nối tới API: {base_url} với model {self.model_name}...")
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        
        if self.use_mock:
            logger.info("Môi trường Local/Test: Kích hoạt chế độ Intelligent Mock LLM Evaluator để test tốc độ cao.")

    def generate_response(self, prompt: str) -> str:
        """Hàm thực thi Suy nghĩ & Trả về phản hồi (Inference / Generation)."""
        if self.use_mock:
            time.sleep(0.02) # Giả lập thời gian xử lý AI
            is_risky = any(k in prompt.lower() for k in ["strcpy", "gets", "sprintf", "bad_", "vuln", "overflow", "leak"])
            pred = 1 if is_risky else 0
            return str(pred)

        # Chạy thực thi Inference trên API
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
        max_retries: int = 5,
        request_delay: float = 0.05
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Đánh giá hàng loạt trên danh sách mẫu kiểm thử (Batch Evaluation):
        - Có kiểm tra Checkpoint cũ để khôi phục tiến trình lập tức.
        - Có cơ chế cơ cấu lại lời gọi (Exponential Backoff) nếu gặp sự cố Rate Limit (429) hoặc quá tải mạng.
        - Trả về toàn bộ danh sách kết quả và ma trận đánh giá.
        """
        from tqdm import tqdm
        ckpt_manager = CheckpointManager(experiment_name=experiment_name)
        total = len(test_samples)
        logger.info(f"Bắt đầu quy trình Đánh Giá (Evaluator) cho {total} mẫu [Experiment: {experiment_name}]...")
        
        correct_count = 0
        total_processed = 0

        # Phục hồi bộ đếm cho thanh tiến độ
        for r in ckpt_manager.loaded_results:
            if r["prediction"] == r["target"]:
                correct_count += 1
            total_processed += 1

        pbar = tqdm(test_samples, desc="Evaluating", unit="sample")
        for sample in pbar:
            sample_id = sample.get("id", f"sample_{total_processed}")
            
            if ckpt_manager.is_completed(sample_id):
                # Đã hoàn thành, bỏ qua
                pass
            else:
                prompt = build_grace_prompt(sample, include_demonstration=include_demonstration)
                
                llm_response = ""
                for attempt in range(1, max_retries + 1):
                    try:
                        llm_response = self.generate_response(prompt)
                        if request_delay > 0 and not self.use_mock:
                            time.sleep(request_delay)
                        break
                    except Exception as e:
                        err_str = str(e)
                        wait_time = min(60, (2 ** attempt) + 1)
                        if "429" in err_str or "rate" in err_str.lower() or "too many" in err_str.lower():
                            wait_time = max(wait_time, 20)
                        logger.warning(f"Lỗi Inference tại ID '{sample_id}' (Lần thử {attempt}/{max_retries}: {e}). Đang đợi {wait_time}s để thử lại...")
                        time.sleep(wait_time)
                        if attempt == max_retries:
                            logger.error(f"Thất bại hoàn toàn khi gọi LLM cho ID '{sample_id}'. Bỏ trống kết quả.")
                            
                pred_int, parse_desc = parse_llm_prediction(llm_response)
                ground_truth = sample.get("target", 0)
                
                record = {
                    "id": sample_id,
                    "target": ground_truth,
                    "prediction": pred_int,
                    "parse_method": parse_desc,
                    "func_snippet": sample.get("func", "")[:120],
                    "llm_raw_response": llm_response,
                    "eval_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                ckpt_manager.save_record(record)
                
                if ground_truth == pred_int:
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
