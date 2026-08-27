import vertexai
from vertexai.generative_models import GenerativeModel
import json
import csv
import logging

# === Vertex AI (thay cho GPT-4 trong paper) ===
vertexai.init(project="grace-enhanced", location="global")
model = GenerativeModel("publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas")

# === Prompt đúng paper ===
templates = {
    1: ("In the above code snippet, check for potential security vulnerabilities "
        "and output either 'Vulnerable' or 'Non-vulnerable'. "
        "You are now an excellent programmer."
        "You are conducting a function vulnerability detection task for C/C++ language."),
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fh = logging.FileHandler('devignmetrics_basep.log')
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(fh)


def extract_prediction(text):
    """Trích xuất kết quả bằng keyword matching (robust hơn exact match)."""
    text_lower = text.strip().lower()
    if 'non-vulnerable' in text_lower or 'non vulnerable' in text_lower:
        return 0
    elif 'vulnerable' in text_lower:
        return 1
    # Fallback: thử tìm số 0 hoặc 1
    text_clean = text.strip().replace('`', '').strip()
    if text_clean == '0':
        return 0
    elif text_clean == '1':
        return 1
    return 2


def main():
    with open('devign_test_processed.json', 'r') as f:
        data = json.load(f)

    def calculate_metrics(preds, truths):
        tp = sum(1 for p, t in zip(preds, truths) if p == t == 1)
        tn = sum(1 for p, t in zip(preds, truths) if p == t == 0)
        fp = sum(1 for p, t in zip(preds, truths) if p == 1 and t == 0)
        fn = sum(1 for p, t in zip(preds, truths) if p == 0 and t == 1)
        n = len(preds)
        acc = (tp + tn) / n if n else 0
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        return acc, prec, rec, f1

    prediction_ls = []
    ground_truth = []

    for row in data:
        inputCode = row['func'][:4000]
        prompt = inputCode + templates[1]

        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
        except Exception as e:
            logger.error(f"Error: {e}")
            raw = ""

        prediction = extract_prediction(raw)
        print(f"Raw: {raw[:80]}... => {prediction}")

        prediction_ls.append(prediction)
        ground_truth.append(row['target'])

        # Lưu tiến trình
        with open('devignresults_basep.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Prediction', 'Groundtruth'])
            writer.writerows(zip(prediction_ls, ground_truth))

        acc, prec, rec, f1 = calculate_metrics(prediction_ls, ground_truth)
        msg = f"[{len(prediction_ls)}/{len(data)}] Acc:{acc:.4f} P:{prec:.4f} R:{rec:.4f} F1:{f1:.4f}"
        print(msg)
        logger.info(msg)


if __name__ == '__main__':
    main()
