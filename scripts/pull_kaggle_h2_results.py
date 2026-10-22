"""Download only H2 outputs and log, excluding the cloned repository."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import requests
from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest


def main():
    root = Path(__file__).resolve().parents[1]/'artifacts/retrieval_h2_kaggle_run'
    root.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    token = ''
    downloads = []
    seen = set()
    while True:
        request = ApiListKernelSessionOutputRequest()
        request.user_name = 'huuhieu3333'
        request.kernel_slug = 'grace-h2-shared-top50-r0-r1'
        request.page_size = 100
        if token:
            request.page_token = token
        with api.build_kaggle_client() as client:
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
        if response.log:
            (root/'run.log').write_text(response.log, encoding='utf-8')
        for item in response.files:
            name = PurePosixPath(item.file_name)
            if name.parts[:1] != ('h2_output',) or '..' in name.parts:
                continue
            path = root.joinpath(*name.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            result = requests.get(item.url, timeout=180)
            result.raise_for_status()
            path.write_bytes(result.content)
            downloads.append(dict(file=name.as_posix(), size=len(result.content),
                                  sha256=hashlib.sha256(result.content).hexdigest()))
            print(name.as_posix(), len(result.content), flush=True)
        token = response.next_page_token
        if not token:
            break
        if token in seen:
            raise RuntimeError('Repeated output pagination token')
        seen.add(token)
    (root/'download_manifest.json').write_text(json.dumps(downloads, indent=2), encoding='utf-8')
    print('Downloaded', len(downloads), 'H2 files')


if __name__ == '__main__':
    main()
