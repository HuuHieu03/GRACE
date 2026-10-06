import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def compute_classification_metrics(y_true: List[int], y_pred: List[Optional[int]]) -> Dict[str, Any]:
    """
    Tính toán toàn diện các chỉ số phân loại nhị phân cho nhiệm vụ phát hiện lỗ hổng
    theo quy chuẩn nghiên cứu khoa học chặt chẽ (STEP 1 & STEP 2 Action Plan):
    - 0: Safe / Non-vulnerable
    - 1: Vulnerable / Có lỗ hổng
    - None: Invalid / Unparseable (Được tính vào tỉ lệ invalid_rate)
    
    Bao gồm:
    - Confusion Matrix (TP, FP, TN, FN)
    - Accuracy, Precision, Recall, F1-Score
    - MCC (Matthews Correlation Coefficient)
    - Balanced Accuracy
    - Predicted Vulnerable Rate
    - Invalid Rate
    - Trivial Baselines: Always-Vulnerable & Always-Non-Vulnerable
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Độ dài nhãn thực tế ({len(y_true)}) và dự đoán ({len(y_pred)}) không khớp!")
        
    n_total = len(y_true)
    if n_total == 0:
        return {
            "total_samples": 0,
            "valid_samples": 0,
            "invalid_samples": 0,
            "invalid_rate": 0.0,
            "accuracy": 0.0,
            "precision": None,
            "recall": None,
            "f1_score": 0.0,
            "mcc": None,
            "balanced_accuracy": 0.0,
            "predicted_vulnerable_rate": 0.0,
            "confusion_matrix": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
            "baselines": {
                "always_vulnerable_f1": 0.0,
                "always_vulnerable_acc": 0.0,
                "always_safe_f1": 0.0,
                "always_safe_acc": 0.0,
            }
        }

    # Đếm số mẫu hợp lệ vs không hợp lệ
    valid_pairs = [(yt, yp) for yt, yp in zip(y_true, y_pred) if yp is not None]
    n_valid = len(valid_pairs)
    n_invalid = n_total - n_valid
    invalid_rate = round(n_invalid / float(n_total), 4)

    # Tính phân phối thực tế trên toàn bộ tập mẫu
    n_true_vuln = sum(1 for yt in y_true if yt == 1)
    n_true_safe = sum(1 for yt in y_true if yt == 0)
    p_vuln = n_true_vuln / float(n_total) if n_total > 0 else 0.0

    # Trivial baseline F1 & Acc trên toàn bộ tập
    always_vuln_acc = round(n_true_vuln / float(n_total), 4)
    always_vuln_f1 = round((2.0 * p_vuln) / (1.0 + p_vuln), 4) if (1.0 + p_vuln) > 0 else 0.0
    always_safe_acc = round(n_true_safe / float(n_total), 4)
    always_safe_f1 = 0.0  # F1 trên class 1 khi luôn đoán 0 là 0.0

    if n_valid == 0:
        return {
            "total_samples": n_total,
            "valid_samples": 0,
            "invalid_samples": n_invalid,
            "invalid_rate": invalid_rate,
            "accuracy": 0.0,
            "precision": None,
            "recall": None,
            "f1_score": 0.0,
            "mcc": None,
            "balanced_accuracy": 0.0,
            "predicted_vulnerable_rate": 0.0,
            "confusion_matrix": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
            "baselines": {
                "always_vulnerable_f1": always_vuln_f1,
                "always_vulnerable_acc": always_vuln_acc,
                "always_safe_f1": always_safe_f1,
                "always_safe_acc": always_safe_acc,
            }
        }

    tp = sum(1 for yt, yp in valid_pairs if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in valid_pairs if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in valid_pairs if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in valid_pairs if yt == 1 and yp == 0)

    accuracy = (tp + tn) / float(n_valid)
    precision = (tp / float(tp + fp)) if (tp + fp) > 0 else None
    recall = (tp / float(tp + fn)) if (tp + fn) > 0 else None
    
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1_score = (2 * precision * recall) / (precision + recall)
    else:
        f1_score = 0.0

    # Recall của lớp an toàn (TNR / Specificity)
    specificity = (tn / float(tn + fp)) if (tn + fp) > 0 else 0.0
    recall_val = recall if recall is not None else 0.0
    balanced_acc = (recall_val + specificity) / 2.0

    # Matthews Correlation Coefficient (MCC)
    mcc_numerator = (tp * tn) - (fp * fn)
    mcc_denominator = math.sqrt(float((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)))
    if mcc_denominator > 0:
        mcc = mcc_numerator / mcc_denominator
    else:
        mcc = None

    pred_vuln_rate = (tp + fp) / float(n_valid)

    return {
        "total_samples": n_total,
        "valid_samples": n_valid,
        "invalid_samples": n_invalid,
        "invalid_rate": invalid_rate,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1_score": round(f1_score, 4),
        "mcc": round(mcc, 4) if mcc is not None else None,
        "balanced_accuracy": round(balanced_acc, 4),
        "predicted_vulnerable_rate": round(pred_vuln_rate, 4),
        "confusion_matrix": {
            "TP (True Positive)": tp,
            "FP (False Positive - Alarm)": fp,
            "TN (True Negative)": tn,
            "FN (False Negative - Miss)": fn
        },
        "baselines": {
            "always_vulnerable_f1": always_vuln_f1,
            "always_vulnerable_acc": always_vuln_acc,
            "always_safe_f1": always_safe_f1,
            "always_safe_acc": always_safe_acc,
        }
    }


def print_metrics_summary(metrics: Dict[str, Any], dataset_name: str = "Evaluation Subset"):
    """In ra bảng báo cáo chỉ số nghiệm thu chuẩn khoa học đầy đủ các tiêu chuẩn mới."""
    cm = metrics.get("confusion_matrix", {})
    bl = metrics.get("baselines", {})
    mcc_str = f"{metrics.get('mcc')}" if metrics.get('mcc') is not None else "N/A"
    prec_str = f"{metrics.get('precision')}" if metrics.get('precision') is not None else "N/A"
    rec_str = f"{metrics.get('recall')}" if metrics.get('recall') is not None else "N/A"

    print("\n" + "+" * 72)
    print(f"|  BẢNG BÁO CÁO KẾT QUẢ ĐÁNH GIÁ CHUẨN KHOA HỌC - [{dataset_name:<20}] |")
    print("+" * 72)
    print(f"| - Tổng số mẫu (Total / Valid / Invalid):  {metrics.get('total_samples', 0)} / {metrics.get('valid_samples', 0)} / {metrics.get('invalid_samples', 0)} (Rate: {metrics.get('invalid_rate', 0.0):.2%}) |")
    print(f"| - MCC (Matthews Correlation Coeff):       {mcc_str:<28} |")
    print(f"| - Balanced Accuracy (Cân bằng 2 lớp):     {metrics.get('balanced_accuracy', 0.0):<28} |")
    print(f"| - F1-SCORE (Chỉ số F1 lớp lỗi):          {metrics.get('f1_score', 0.0):<28} |")
    print(f"| - Precision / Recall:                     {prec_str} / {rec_str} |")
    print(f"| - Accuracy toàn cục:                      {metrics.get('accuracy', 0.0):<28} |")
    print(f"| - Predicted Vulnerable Rate:              {metrics.get('predicted_vulnerable_rate', 0.0):.2%} |")
    print("-" * 72)
    print("| MA TRẬN NHẦM LẪN (CONFUSION MATRIX):                                  |")
    print(f"|   [+] True Positive  (Đoán đúng Có lỗi):  {cm.get('TP (True Positive)', 0):<26} |")
    print(f"|   [-] False Negative (Bỏ sót Lỗ hổng):   {cm.get('FN (False Negative - Miss)', 0):<26} |")
    print(f"|   [+] True Negative  (Đoán đúng An toàn): {cm.get('TN (True Negative)', 0):<26} |")
    print(f"|   [-] False Positive (Báo động Giả):      {cm.get('FP (False Positive - Alarm)', 0):<26} |")
    print("-" * 72)
    print("| ĐỐI CHỨNG TẦM THƯỜNG (TRIVIAL BASELINES):                             |")
    print(f"|   * Always-Vulnerable (Luôn đoán 1): F1={bl.get('always_vulnerable_f1', 0.0):<7} | Acc={bl.get('always_vulnerable_acc', 0.0):<7} (MCC=0)   |")
    print(f"|   * Always-Non-Vuln  (Luôn đoán 0): F1={bl.get('always_safe_f1', 0.0):<7} | Acc={bl.get('always_safe_acc', 0.0):<7} (MCC=0)   |")
    print("+" * 72 + "\n")

