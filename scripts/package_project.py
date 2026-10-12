"""Reproducible allowlist archive. Never include user data, models or secrets."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import zipfile

ROOT=Path(__file__).resolve().parent.parent
TOP_FILES={
    'app.py','pyproject.toml','constraints.txt','.env.example','.gitignore',
    'requirements-base.txt','requirements-dev.txt','requirements-embeddings.txt',
    'requirements-faiss.txt','requirements-reranking.txt','README.md','SETUP_WINDOWS.md',
    'SETUP_MAC.md','DATA_SOURCES.md','EVALUATION.md','LIMITATIONS.md','BUILD_STATUS.md','AGENTS.md',
}
DIRECTORIES={'vidhaan','scripts','configs','docs','tests'}
SUFFIXES={'.py','.ps1','.sh','.md','.txt','.json','.csv','.svg'}
REPORT_FILES={
    'data/registry/source_manifest.json','data/registry/source_inventory.json',
    'data/registry/acquisition_sample.json','evaluations/benchmark.json','evaluations/fixture_benchmark.json',
    'evaluations/latest/results.json','evaluations/latest/results.csv',
    'evaluations/development/results.json','evaluations/development/results.csv',
    'evaluations/fixtures/results.json','evaluations/fixtures/results.csv',
    'evaluations/validation.json','evaluations/pytest.xml','evaluations/dependency_versions.txt',
    'evaluations/extracted_validation.json','evaluations/ui_smoke.json',
    'evaluations/threshold_tuning.json',
    'data/registry/acquisition_expansion.json','data/registry/acquisition_discovery.json',
    'evaluations/corpus_expansion_smoke.json','evaluations/expansion_export_validation.json',
    'evaluations/bundle_validation.json','evaluations/bundled/results.json','evaluations/bundled/results.csv',
    'evaluations/bundled/benchmark.json',
    'evaluations/web_validation.json',
}
FRONTEND_FILES={'frontend/package.json','frontend/package-lock.json','frontend/index.html',
                'frontend/vite.config.js','frontend/playwright.config.js',
                'frontend/src/main.jsx','frontend/src/style.css','frontend/tests/workspace.spec.js'}


def selected_files(root):
    root=Path(root).resolve()
    files=[]
    bundle_files=set()
    if (root/'data/bundled/manifest.json').exists():
        from vidhaan.bundled import verify_bundle
        _,selected=verify_bundle(root/'data/bundled')
        bundle_files={root/'data/bundled/manifest.json',*selected.values()}
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file():continue
        parts=relative.parts
        if any(p in {'.git','.venv','__pycache__','.pytest_cache','private','.cache','node_modules','test-results','playwright-report'} for p in parts):continue
        web_asset=(len(parts)==4 and parts[:3]==('vidhaan','web','assets') and
                   path.suffix in {'.js','.css','.woff','.woff2'} and
                   re.fullmatch(r'[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8}\.(js|css|woff2?)',path.name))
        web_entry=relative.as_posix()=='vidhaan/web/index.html'
        allowed=(path in bundle_files or len(parts)==1 and path.name in TOP_FILES or relative.as_posix() in REPORT_FILES or
                 relative.as_posix() in FRONTEND_FILES or web_asset or web_entry or
                 parts[0] in DIRECTORIES and parts[:2]!=('vidhaan','web') and
                 path.suffix in SUFFIXES and path.name not in {'.env','secrets.txt'})
        if not allowed:continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f'Refusing archive symlink or escaped file: {relative}')
        files.append(path)
    return files


def build_archive(root=ROOT,output=None):
    root=Path(root).resolve();output=Path(output or root/'dist/Vidhaan_University_RAG.zip')
    output.parent.mkdir(parents=True,exist_ok=True)
    files=selected_files(root)
    if not (root/'app.py') in files or not (root/'pyproject.toml') in files:
        raise ValueError('Incomplete project; app.py and pyproject.toml are required')
    inventory={}
    temp=output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:
            name='vidhaan/'+path.relative_to(root).as_posix()
            content=path.read_bytes()
            info=zipfile.ZipInfo(name,date_time=(2026,10,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if path.suffix=='.sh' else 0o100644)<<16
            archive.writestr(info,content)
            inventory[name]=hashlib.sha256(content).hexdigest()
        archive.writestr('vidhaan/PACKAGE_MANIFEST.json',json.dumps(inventory,indent=2))
        for folder in ['data/raw','data/processed','data/indexes','data/registry']:
            archive.writestr('vidhaan/'+folder+'/.gitkeep','')
    with zipfile.ZipFile(temp) as archive:
        if archive.testzip():raise ValueError('ZIP integrity check failed')
        if any(not n.startswith('vidhaan/') or '..' in Path(n).parts for n in archive.namelist()):
            raise ValueError('Unsafe archive path')
    temp.replace(output)
    return {'path':str(output),'files':len(inventory),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    print(json.dumps(build_archive(output=args.output),indent=2))
