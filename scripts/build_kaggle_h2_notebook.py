"""Build H2 Kaggle notebook cloning an exact, reviewed Git revision."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    if len(args.revision) != 40 or any(c not in '0123456789abcdef' for c in args.revision):
        parser.error('revision must be a full Git SHA')
    folder = ROOT/'kaggle_notebooks/retrieval_h2'
    folder.mkdir(parents=True, exist_ok=True)
    setup = f'''import os, sys, subprocess, json
from pathlib import Path
REVISION = {args.revision!r}
workspace = Path('/kaggle/working/GRACE')
subprocess.run(['git', 'clone', 'https://github.com/HuuHieu03/GRACE.git', str(workspace)], check=True)
subprocess.run(['git', '-C', str(workspace), 'checkout', '--detach', REVISION], check=True)
actual = subprocess.check_output(['git', '-C', str(workspace), 'rev-parse', 'HEAD'], text=True).strip()
assert actual == REVISION
print('Frozen code revision:', actual, flush=True)
os.chdir(workspace)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'transformers==5.1.0', 'safetensors>=0.4.3', 'pytest'], check=True)
import torch
print('PyTorch:', torch.__version__, 'CUDA:', torch.cuda.is_available(), flush=True)
assert torch.cuda.is_available(), 'H2 requires an enabled GPU for this run'
subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_retrieval_h2.py', 'tests/test_sink_evidence_v12.py', '-q'], check=True)
'''
    run = '''from huggingface_hub import snapshot_download
tokenizer_path = snapshot_download('Salesforce/codet5-base',
    revision='02cd2d31bb7c6d0e4d91156167b2de044989c733',
    allow_patterns=['config.json', 'vocab.json', 'merges.txt'])
weights_path = snapshot_download('Salesforce/codet5-base',
    revision='fcedbb79ad3190afe5a987160e044f23d1a7c20c',
    allow_patterns=['model.safetensors'])
output = Path('/kaggle/working/h2_output')
output.mkdir(exist_ok=True)
(output/'git_revision.json').write_text(json.dumps({'revision': REVISION}), encoding='utf-8')
subprocess.run([sys.executable, '-u', 'scripts/run_retrieval_h2.py',
    '--model', weights_path, '--tokenizer', tokenizer_path,
    '--device', 'cuda', '--batch-size', '8', '--output', str(output)], check=True)
summary = json.loads((output/'summary.json').read_text(encoding='utf-8'))
print(json.dumps(summary, indent=2), flush=True)
'''
    cells = [dict(cell_type='markdown', metadata={}, source=[
        '# GRACE H2: shared top-50 R0 vs R1\n',
        'Full Devign train / canonical dev100. Code and model revisions are pinned. '
        'No LLM calls. Selection diagnostics do not establish relevance or prediction quality.'])]
    for code in [setup, run]:
        cells.append(dict(cell_type='code', execution_count=None, metadata={}, outputs=[],
                          source=code.splitlines(keepends=True)))
    notebook = dict(cells=cells, nbformat=4, nbformat_minor=5,
                    metadata=dict(kernelspec=dict(name='python3', display_name='Python 3', language='python')))
    metadata = dict(id='huuhieu3333/grace-h2-shared-top50-r0-r1',
                    title='GRACE H2 Shared Top50 R0 R1', code_file='retrieval_h2_kaggle.ipynb',
                    language='python', kernel_type='notebook', is_private='true',
                    enable_gpu='true', enable_internet='true', dataset_sources=[])
    (folder/'retrieval_h2_kaggle.ipynb').write_text(json.dumps(notebook, indent=2), encoding='utf-8')
    (folder/'kernel-metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('Generated notebook for revision', args.revision)


if __name__ == '__main__':
    main()
