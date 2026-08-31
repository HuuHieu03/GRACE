"""
GRACE Data Loader Module
Tải bộ dữ liệu lỗ hổng phần mềm từ Hugging Face (Devign, Reveal) hoặc file JSON cục bộ,
chuẩn hóa định dạng và cắt mẫu ngẫu nhiên cân bằng tỷ lệ nhãn (Stratified Slicing).
"""

import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def standardize_sample(raw_item: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """
    Chuẩn hóa 1 mẫu dữ liệu thô từ Hugging Face / JSON thành định dạng tiêu chuẩn của GRACE.
    
    Định dạng chuẩn:
    - id: ID duy nhất (str)
    - func: Đoạn mã nguồn hàm C/C++ (str)
    - target: Nhãn lỗ hổng (int: 0 = An toàn, 1 = Có lỗ hổng)
    - nodes: Danh sách nút đồ thị CPG/AST (list, mặc định [])
    - edges: Danh sách cạnh đồ thị CFG/PDG (list, mặc định [])
    """
    # Lấy hàm code C/C++ từ các tên trường phổ biến
    func_code = (
        raw_item.get("func") or 
        raw_item.get("function") or 
        raw_item.get("code") or 
        raw_item.get("processed_func") or ""
    )
    
    # Lấy nhãn target
    raw_target = raw_item.get("target", raw_item.get("label", 0))
    try:
        target = int(raw_target)
    except (ValueError, TypeError):
        target = 0
        
    raw_id = raw_item.get("id", raw_item.get("idx"))
    if raw_id is not None and str(raw_id).strip() != "":
        sample_id = f"{raw_id}_{idx}"
    else:
        sample_id = f"sample_{idx}"
    nodes = raw_item.get("node", raw_item.get("nodes", []))
    edges = raw_item.get("edge", raw_item.get("edges", []))
    
    return {
        "id": sample_id,
        "func": str(func_code).strip(),
        "target": target,
        "nodes": nodes if isinstance(nodes, list) else [],
        "edges": edges if isinstance(edges, list) else [],
        "raw": raw_item
    }


def slice_dataset(
    dataset: List[Dict[str, Any]], 
    ratio: float = 0.05, 
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Trích xuất một tỷ lệ mẩu dữ liệu (ví dụ 5%) nhưng bảo toàn cân bằng tỷ lệ nhãn (Stratified Sampling).
    
    Args:
        dataset: Danh sách các mẫu đã chuẩn hóa.
        ratio: Tỷ lệ trích xuất (0.0 < ratio <= 1.0).
        seed: Random seed để tái tạo kết quả.
        
    Returns:
        Danh sách mẫu đã được cắt nhỏ theo tỷ lệ.
    """
    if ratio >= 1.0:
        return dataset
        
    if ratio <= 0.0:
        raise ValueError("Tỷ lệ ratio phải lớn hơn 0.0")
        
    # Phân nhóm theo nhãn
    vuln_samples = [s for s in dataset if s["target"] == 1]
    safe_samples = [s for s in dataset if s["target"] == 0]
    
    # Thiết lập seed
    random_gen = random.Random(seed)
    
    # Tính số lượng lấy cho từng nhóm
    num_vuln = max(1, int(len(vuln_samples) * ratio)) if vuln_samples else 0
    num_safe = max(1, int(len(safe_samples) * ratio)) if safe_samples else 0
    
    sampled_vuln = random_gen.sample(vuln_samples, num_vuln) if num_vuln <= len(vuln_samples) else vuln_samples
    sampled_safe = random_gen.sample(safe_samples, num_safe) if num_safe <= len(safe_samples) else safe_samples
    
    sliced = sampled_vuln + sampled_safe
    random_gen.shuffle(sliced)
    
    logger.info(
        f"Trích xuất {ratio*100:.1f}% dataset: Tổng {len(sliced)} mẫu "
        f"({len(sampled_vuln)} Vulnerable, {len(sampled_safe)} Safe) từ gốc {len(dataset)} mẫu."
    )
    return sliced


def stream_json_array(file_path: Path, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    """Đọc file JSON mảng đối tượng lớn theo cơ chế luồng (Streaming) để tránh tràn bộ nhớ RAM."""
    import json
    items = []
    current_obj_lines = []
    in_obj = False
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("  {"):
                in_obj = True
                current_obj_lines = [line]
            elif in_obj:
                current_obj_lines.append(line)
                if line.startswith("  }") or line.startswith("  },"):
                    in_obj = False
                    raw_str = "".join(current_obj_lines).rstrip().rstrip(",")
                    try:
                        items.append(json.loads(raw_str))
                    except Exception:
                        pass
                    if max_items is not None and len(items) >= max_items:
                        break
    return items


def load_hf_dataset(
    dataset_name: str = "DetectVul/devign", 
    split: str = "test",
    sample_ratio: float = 1.0,
    max_samples: Optional[int] = None,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """
    Tải bộ dữ liệu: Ưu tiên tải từ file JSON đã trích xuất đồ thị Joern trong data/processed/.
    Nếu không có, tải từ Hugging Face qua thư viện `datasets`.
    Nếu không có internet/lỗi, tự động fallback về mock data.
    """
    raw_list = None
    
    # 1. Kiểm tra file cục bộ đã trích xuất CPG đồ thị Joern
    name_clean = dataset_name.strip().lower()
    dataset_key = None
    if name_clean in ["detectvul/devign", "devign"]:
        dataset_key = "devign"
    elif name_clean in ["sensorllm/reveal", "reveal"]:
        dataset_key = "reveal"
        
    if dataset_key:
        local_candidates = [
            config.data_dir / "processed" / f"{dataset_key}_{split}_processed.json",
            config.base_dir / "data" / "processed" / f"{dataset_key}_{split}_processed.json",
            Path("data/processed") / f"{dataset_key}_{split}_processed.json"
        ]
        for p in local_candidates:
            if p.exists():
                logger.info(f"Phát hiện file dữ liệu đã trích xuất đồ thị CPG cục bộ: {p}. Đang nạp (max_samples={max_samples})...")
                # Nếu file > 500MB hoặc có max_samples, dùng stream_json_array để tiết kiệm RAM
                file_size_mb = p.stat().st_size / (1024 * 1024)
                if file_size_mb > 500 or max_samples is not None:
                    raw_list = stream_json_array(p, max_items=max_samples)
                else:
                    import json
                    with open(p, "r", encoding="utf-8") as f:
                        raw_list = json.load(f)
                logger.info(f"Nạp thành công {len(raw_list)} mẫu đã có đầy đủ đồ thị Joern từ {p.name}.")
                break
                
    # 2. Tải từ Hugging Face nếu không có file cục bộ
    if raw_list is None:
        logger.info(f"Đang tải dataset '{dataset_name}' (split='{split}') từ Hugging Face...")
        try:
            from datasets import load_dataset
            hf_ds = load_dataset(dataset_name, split=split)
            raw_list = list(hf_ds)
            if max_samples is not None:
                raw_list = raw_list[:max_samples]
            logger.info(f"Tải thành công {len(raw_list)} mẫu thô từ Hugging Face.")
        except Exception as e:
            logger.warning(f"Không thể tải từ Hugging Face ({e}). Chuyển sang chế độ Fallback Mock Data...")
            raw_list = generate_mock_dataset(num_samples=max_samples if max_samples else 50)

    # Chuẩn hóa
    standardized = [standardize_sample(item, i) for i, item in enumerate(raw_list)]
    
    # Cắt mẩu nếu sample_ratio < 1.0
    if sample_ratio < 1.0:
        standardized = slice_dataset(standardized, ratio=sample_ratio, seed=seed)
        
    return standardized


def generate_mock_dataset(num_samples: int = 20) -> List[Dict[str, Any]]:
    """Tạo bộ dữ liệu giả lập cho mục đích kiểm thử tự động (Unit Test / Offline Test)."""
    mock_data = []
    for i in range(num_samples):
        is_vuln = 1 if i % 2 == 0 else 0
        code = (
            f"void handle_buffer_{i}(char *user_input) {{\n"
            f"    char buf[64];\n"
            f"    {'strcpy(buf, user_input);' if is_vuln else 'strncpy(buf, user_input, sizeof(buf)-1);'}\n"
            f"}}"
        )
        mock_data.append({
            "id": f"mock_{i}",
            "func": code,
            "target": is_vuln,
            "node": [{"id": 0, "label": "AST_FUNC_DEF"}],
            "edge": [{"source": 0, "target": 1, "type": "CFG"}]
        })
    return mock_data
