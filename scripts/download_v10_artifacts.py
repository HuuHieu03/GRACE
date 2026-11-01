import os
import sys
import requests
from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest

sys.stdout.reconfigure(encoding="utf-8")

api = KaggleApi()
api.authenticate()

target_dir = "data/kaggle_run_v10_output"
os.makedirs(target_dir, exist_ok=True)

print("Connecting to Kaggle client...")
with api.build_kaggle_client() as kaggle:
    token = None
    page = 0
    total_downloaded = 0
    while True:
        req = ApiListKernelSessionOutputRequest()
        req.user_name = "huuhieu3333"
        req.kernel_slug = "grace-host-llm-server"
        req.page_size = 500
        if token:
            req.page_token = token
        resp = kaggle.kernels.kernels_api_client.list_kernel_session_output(req)
        print(f"Page {page}: received {len(resp.files)} files (next token: {bool(resp.next_page_token)})")
        for item in resp.files:
            fname = item.file_name
            # Download zip, csv, png, json, jsonl, but skip individual cache files in _cache/
            if "_cache/" in fname or "_cache\\" in fname:
                continue
            print(f"  Downloading: {fname}...")
            outpath = os.path.join(target_dir, fname)
            os.makedirs(os.path.dirname(outpath), exist_ok=True)
            r = requests.get(item.url, stream=True)
            with open(outpath, "wb") as f:
                f.write(r.content)
            size = os.path.getsize(outpath)
            print(f"  -> Saved {outpath} ({size:,} bytes)")
            total_downloaded += 1

        token = resp.next_page_token
        page += 1
        if not token:
            break

print(f"\n[DONE] Downloaded {total_downloaded} key artifact files across {page} pages!")
