import json
import openai
import os
import io
import sys
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("FPT_API_KEY"), base_url=os.getenv("FPT_BASE_URL"))

with open("data/processed/devign_test_processed.json", "r", encoding="utf-8") as f:
    sample = json.load(f)[1]

from prompt_engine import build_grace_prompt
prompt = build_grace_prompt(sample, include_demonstration=False)

candidate_models = [
    "gemma-4-26B-A4B-it",
    "gemma-4-31B-it",
    "Llama-3.3-70B-Instruct",
    "gpt-oss-20b",
    "gpt-oss-120b"
]

print("="*75)
print("KHẢO SÁT HÀNH VI SINH CỦA CÁC MÔ HÌNH VỚI GRACE PROMPT (max_tokens=128)")
print("="*75)

for m in candidate_models:
    try:
        resp = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=128
        )
        msg = resp.choices[0].message
        reasoning = getattr(msg, "reasoning_content", None)
        print(f"\n[*] Model: {m}")
        print(f"    - Finish reason : {resp.choices[0].finish_reason}")
        print(f"    - Content       : {repr(msg.content)}")
        print(f"    - Has reasoning : {'Yes (' + str(len(reasoning)) + ' chars)' if reasoning else 'No'}")
    except Exception as e:
        print(f"\n[*] Model: {m} -> ERROR: {e}")
