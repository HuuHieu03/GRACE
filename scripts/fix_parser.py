import json

nb_path = "kaggle_notebooks/h2_vertex_eval/h2_vertex_eval_kaggle.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb["cells"]:
    if cell.get("cell_type") == "code" and any("ExactLastLineBinaryParser" in l for l in cell.get("source", [])):
        new_source = []
        skip = False
        for line in cell["source"]:
            if "class ExactLastLineBinaryParser:" in line:
                skip = True
                new_source.extend([
                    "class ExactLastLineBinaryParser:\n",
                    '    """Strict parser conforming to evaluation_contract.yaml exact_last_line_binary."""\n',
                    "    @staticmethod\n",
                    "    def parse(raw_text: str):\n",
                    "        if not isinstance(raw_text, str) or not raw_text.strip():\n",
                    '            return None, "invalid"\n',
                    "        \n",
                    "        last_line = next(\n",
                    "            (line.strip() for line in reversed(raw_text.splitlines()) if line.strip()),\n",
                    '            "",\n',
                    "        )\n",
                    '        if last_line == "1":\n',
                    '            return 1, "valid"\n',
                    '        if last_line == "0":\n',
                    '            return 0, "valid"\n',
                    '        return None, "invalid"\n',
                    "\n"
                ])
            elif skip and "class VertexAIDeepSeekClient:" in line:
                skip = False
                new_source.append(line)
            elif not skip:
                new_source.append(line)
        cell["source"] = new_source

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("Canonical parser written to notebook successfully!")
