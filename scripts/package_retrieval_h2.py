"""Build a minimal Kaggle upload ZIP; never include credentials or git files."""
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = [ROOT/'scripts/run_retrieval_h2.py',
             ROOT/'data/processed/devign_train_compact_cpg.json',
             ROOT/'data/splits/devign_dev_clean_100_ids.json',
             ROOT/'project_docs/reports/retrieval_h2/README.md']
    paths.extend(sorted((ROOT/'src/security_signature').glob('*.py')))
    cells = [dict(cell_type='markdown', metadata={}, source=[
        '# H2 offline retrieval\n',
        'Attach the ZIP contents as a Kaggle dataset, enable GPU and Internet. '
        'This runs full-train CodeT5 retrieval, no LLM requests. '
        'Original IDs and labels are retained only for private traceability.'])]
    code = """from pathlib import Path
import shutil, subprocess, sys
from huggingface_hub import snapshot_download
roots = list(Path('/kaggle/input').rglob('run_retrieval_h2.py'))
assert len(roots) == 1, roots
source = roots[0].parents[1]
workspace = Path('/kaggle/working/h2_package')
shutil.copytree(source, workspace, dirs_exist_ok=True)
model = snapshot_download('Salesforce/codet5-base',
    revision='02cd2d31bb7c6d0e4d91156167b2de044989c733',
    allow_patterns=['config.json', 'vocab.json', 'merges.txt', 'pytorch_model.bin'])
subprocess.run([sys.executable, str(workspace/'scripts/run_retrieval_h2.py'),
    '--train', str(workspace/'data/processed/devign_train_compact_cpg.json'),
    '--queries', str(workspace/'data/splits/devign_dev_clean_100_ids.json'),
    '--model', model, '--tokenizer', model, '--device', 'cuda',
    '--batch-size', '8', '--output', '/kaggle/working/h2_output'], check=True)
"""
    cells.append(dict(cell_type='code', metadata={}, execution_count=None, outputs=[],
                      source=code.splitlines(keepends=True)))
    notebook = dict(cells=cells, metadata=dict(kernelspec=dict(display_name='Python 3', language='python', name='python3')),
                    nbformat=4, nbformat_minor=5)
    output = ROOT/'artifacts/retrieval_h2_package.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr('run_h2_kaggle.ipynb', json.dumps(notebook, indent=2))
    notebook_path = ROOT/'artifacts/run_h2_kaggle.ipynb'
    notebook_path.write_text(json.dumps(notebook, indent=2), encoding='utf-8')
    print(output.name, output.stat().st_size)


if __name__ == '__main__':
    main()
