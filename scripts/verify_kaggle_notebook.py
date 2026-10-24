"""Static verification script for Kaggle notebooks.
Validates 100% of code cells via ast.parse() to guarantee no SyntaxError or IndentationError,
and unit tests ExactLastLineBinaryParser against evaluation contract edge cases.
"""
import ast
import json
import re
import sys
import io
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK = ROOT / "kaggle_notebooks" / "h2_vertex_eval" / "h2_vertex_eval_kaggle.ipynb"


def verify_notebook(notebook_path: Path) -> bool:
    print(f"[*] Validating notebook: {notebook_path}")
    if not notebook_path.exists():
        print(f"[!] Error: Notebook file not found at {notebook_path}")
        return False

    with open(notebook_path, "r", encoding="utf-8") as f:
        try:
            nb = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[!] JSON Decode Error in notebook: {e}")
            return False

    cells = nb.get("cells", [])
    total_cells = len(cells)
    code_cells = 0
    errors = []

    print(f"[*] Total notebook cells: {total_cells}")
    for idx, cell in enumerate(cells):
        cell_type = cell.get("cell_type")
        if cell_type != "code":
            continue

        code_cells += 1
        source_lines = cell.get("source", [])
        source_text = "".join(source_lines) if isinstance(source_lines, list) else str(source_lines)

        try:
            tree = ast.parse(source_text, filename=f"Cell_{idx}")
            node_count = len(list(ast.walk(tree)))
            first_line = source_text.strip().splitlines()[0] if source_text.strip() else "<empty>"
            print(f"  [Cell {idx:02d}] ✓ AST OK ({len(source_lines)} lines, {node_count} AST nodes) -> {first_line[:60]}")
        except (SyntaxError, IndentationError) as e:
            print(f"  [Cell {idx:02d}] ✗ SYNTAX ERROR: {e.msg} at line {e.lineno}, offset {e.offset}")
            if e.text:
                print(f"         Code snippet: {e.text.strip()}")
            errors.append((idx, type(e).__name__, str(e)))
        except Exception as e:
            print(f"  [Cell {idx:02d}] ✗ UNEXPECTED PARSE ERROR: {type(e).__name__}: {e}")
            errors.append((idx, type(e).__name__, str(e)))

    print("-" * 60)
    print(f"[*] Checked {code_cells} code cells out of {total_cells} total cells.")
    if errors:
        print(f"[!] FAILED: Found {len(errors)} syntax/indentation errors across notebook cells!")
        return False

    print("[✓] ALL CODE CELLS PASSED ast.parse() WITHOUT ERRORS!")

    # Verify parser
    print("\n[*] Running unit tests on ExactLastLineBinaryParser...")
    parser_test_cases = [
        ("0", 0, "valid"),
        ("1", 1, "valid"),
        (" 0 ", 0, "valid"),
        (" 1 ", 1, "valid"),
        ("Step 1: thinking\n0", 0, "valid"),
        ("Step 1: thinking\n1", 1, "valid"),
        ("Analysis...\n\n0\n", 0, "valid"),
        ("Analysis...\n\n1\n", 1, "valid"),
        ("", None, "invalid"),
        ("   ", None, "invalid"),
        (None, None, "invalid"),
        ("random text without digit", None, "invalid"),
        ("both 0 and 1", None, "invalid"),
        ("42", None, "invalid"),
        ("'0.'", None, "invalid"),
        ("'1.'", None, "invalid"),
    ]

    parser_code = None
    for cell in cells:
        if cell.get("cell_type") == "code":
            src = "".join(cell.get("source", []))
            if "class ExactLastLineBinaryParser" in src:
                class_lines = []
                in_class = False
                for line in src.splitlines(keepends=True):
                    if "class ExactLastLineBinaryParser" in line:
                        in_class = True
                    elif in_class and line.startswith("class "):
                        break
                    if in_class:
                        class_lines.append(line)
                parser_code = "".join(class_lines)
                break

    if not parser_code:
        print("[!] Warning: ExactLastLineBinaryParser definition not found in notebook.")
        return False

    ns = {}
    try:
        exec(parser_code, ns)
    except Exception as e:
        print(f"[!] Failed to execute parser class in test namespace: {e}")
        return False

    parser_cls = ns.get("ExactLastLineBinaryParser")
    parser_passed = 0
    parser_failed = 0
    for raw_input, exp_val, exp_status in parser_test_cases:
        actual_val, actual_status = parser_cls.parse(raw_input)
        if actual_val == exp_val and actual_status == exp_status:
            parser_passed += 1
        else:
            parser_failed += 1
            print(f"  ✗ Test failed for input: {raw_input!r} -> Expected ({exp_val}, {exp_status!r}), got ({actual_val}, {actual_status!r})")

    if parser_failed > 0:
        print(f"[!] Parser unit tests failed: {parser_failed}/{len(parser_test_cases)} failed.")
        return False
    else:
        print(f"[✓] All {parser_passed} parser test cases passed perfectly!")

    return True


if __name__ == "__main__":
    target_nb = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NOTEBOOK
    success = verify_notebook(target_nb)
    sys.exit(0 if success else 1)
