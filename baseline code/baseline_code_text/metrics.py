"""
GRACE Evaluation Metrics Engine (Stage 3)
Thay thế hoàn toàn bộ đo kiểm NLP lỗi thời (`nlgeval`, BLEU, ROUGE) bằng hệ thống 
chỉ số phân loại bảo mật phần mềm chuẩn: F1-Score, Precision, Recall, Accuracy & Confusion Matrix.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def compute_classification_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    """
    Tính toán toàn diện các chỉ số phân loại nhị phân cho nhiệm vụ phát hiện lỗ hổng:
    - 0: Safe / An toàn
    - 1: Vulnerable / Có lỗ hổng
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Độ dài nhãn thực tế ({len(y_true)}) và dự đoán ({len(y_pred)}) không khớp!")
        
    n_total = len(y_true)
    if n_total == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "confusion_matrix": (0, 0, 0, 0)}

    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)  # True Positive
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)  # False Positive (Báo động giả)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)  # True Negative
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)  # False Negative (Bỏ sót lỗi)

    accuracy = (tp + tn) / float(n_total)
    precision = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = (2 * precision * recall) / float(precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total_samples": n_total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4),
        "confusion_matrix": {
            "TP (True Positive)": tp,
            "FP (False Positive - Alarm)": fp,
            "TN (True Negative)": tn,
            "FN (False Negative - Miss)": fn
        }
    }


def print_metrics_summary(metrics: Dict[str, Any], dataset_name: str = "Evaluation Subset"):
    """In ra bảng báo cáo chỉ số nghiệm thu cực kỳ trực quan và chuyên nghiệp."""
    cm = metrics.get("confusion_matrix", {})
    print("\n" + "+" * 65)
    print(f"|  BẢNG BÁO CÁO KẾT QUẢ ĐÁNH GIÁ GRACE - [{dataset_name:<20}]  |")
    print("+" * 65)
    print(f"| - Tổng số mẫu đánh giá (Total Samples): {metrics.get('total_samples', 0):<23} |")
    print(f"| - F1-SCORE (Chỉ số quyết định):         {metrics.get('f1_score', 0.0):<23} |")
    print(f"| - Precision (Độ chính xác báo lỗi):     {metrics.get('precision', 0.0):<23} |")
    print(f"| - Recall (Độ phủ phát hiện lỗ hổng):    {metrics.get('recall', 0.0):<23} |")
    print(f"| - Accuracy (Tỉ lệ đúng toàn cục):       {metrics.get('accuracy', 0.0):<23} |")
    print("-" * 65)
    print("| MA TRẬN NHẦM LẪN (CONFUSION MATRIX):                              |")
    print(f"|   [+] True Positive  (Đoán đúng Có lỗi):  {cm.get('TP (True Positive)', 0):<21} |")
    print(f"|   [-] False Negative (Bỏ sót Lỗ hổng):   {cm.get('FN (False Negative - Miss)', 0):<21} |")
    print(f"|   [+] True Negative  (Đoán đúng An toàn): {cm.get('TN (True Negative)', 0):<21} |")
    print(f"|   [-] False Positive (Báo động Giả):      {cm.get('FP (False Positive - Alarm)', 0):<21} |")
    print("+" * 65 + "\n")
