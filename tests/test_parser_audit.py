"""
Bộ kiểm thử đơn vị cho Evaluator Parser mới (STEP 2 trong Immediate Action Plan)
Bao phủ:
- '0', '1'
- 'Vulnerable', 'Non-vulnerable'
- 'Non-vulnerable (0)', 'Label: Non-vulnerable (0)'
- 'Vulnerable (1)', 'Label: Vulnerable (1)'
- 'safe', 'not vulnerable', 'not a vulnerability'
- Chuỗi rỗng, khoảng trắng, malformed / unparseable
- Chuỗi mâu thuẫn chứa cả hai từ khóa/nhãn đối lập
Đảm bảo:
- Non-vulnerable -> 0
- Vulnerable -> 1
- Invalid -> None (trạng thái riêng, không ép thành 0)
"""

import pytest
import sys
from pathlib import Path

# Thêm src vào PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evaluator import parse_llm_prediction


@pytest.mark.parametrize(
    "raw_text,expected_pred,expected_valid",
    [
        # 1. Strict / Single digit
        ("0", 0, True),
        ("1", 1, True),
        (" 0 ", 0, True),
        (" 1 ", 1, True),
        ("'0'", 0, True),
        ('"1"', 1, True),
        ("0.", 0, True),
        ("1.", 1, True),

        # 2. Last line digit
        ("Explanation...\n0", 0, True),
        ("Analysis:\nThe result is\n1", 1, True),
        ("Notes...\n0.", 0, True),
        ("Conclusion:\n1.", 1, True),

        # 3. Explicit labels with text and numbers
        ("Vulnerable", 1, True),
        ("Non-vulnerable", 0, True),
        ("non-vulnerable", 0, True),
        ("NON-VULNERABLE", 0, True),
        ("Non-vulnerable (0)", 0, True),
        ("Label: Non-vulnerable (0)", 0, True),
        ("Output: Non-vulnerable (0)", 0, True),
        ("Vulnerable (1)", 1, True),
        ("Label: Vulnerable (1)", 1, True),
        ("Label: 1", 1, True),
        ("Label: 0", 0, True),
        ("The function is safe.", 0, True),
        ("The code is not vulnerable.", 0, True),
        ("Contains a security vulnerability.", 1, True),
        ("No vulnerability detected.", 0, True),

        # 4. Invalid / Malformed / Empty cases -> None (NOT 0!)
        ("", None, False),
        ("   ", None, False),
        ("None", None, False),
        ("I cannot determine whether this code is vulnerable.", None, False),
        ("completely random gibberish 42 xyz", None, False),

        # 5. Contradictory cases -> None (NOT 0!)
        ("It is vulnerable (1) but also safe (0).", None, False),
        ("Both 0 and 1 are possible answers.", None, False),
        ("The code is vulnerable and not vulnerable at the same time.", None, False),
    ]
)
def test_parse_llm_prediction_rigorous(raw_text, expected_pred, expected_valid):
    pred, method, is_valid = parse_llm_prediction(raw_text)
    assert is_valid == expected_valid, f"Failed validity for {raw_text!r}: got {is_valid}, expected {expected_valid}"
    assert pred == expected_pred, f"Failed prediction for {raw_text!r}: got {pred}, expected {expected_pred} (method: {method})"
