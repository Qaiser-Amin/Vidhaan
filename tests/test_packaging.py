import importlib.util
from pathlib import Path
import zipfile
import pytest

spec=importlib.util.spec_from_file_location('packager',Path(__file__).resolve().parents[1]/'scripts/package_project.py')
packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)


def test_archive_boundaries(tmp_path):
    for name in ['app.py','pyproject.toml','vidhaan/__init__.py','.env','data/private/contract.txt',
                 '.venv/secret.py','data/raw/huge.pdf','.git/config','model.safetensors','docs/README.md']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fictional marker')
    output=tmp_path/'dist/test.zip';packager.build_archive(tmp_path,output)
    with zipfile.ZipFile(output) as archive:
        names=archive.namelist();assert archive.testzip() is None
        assert 'vidhaan/app.py' in names and all(n.startswith('vidhaan/') for n in names)
        assert not any('contract' in n or '.env' in n or '.venv' in n or 'huge.pdf' in n or 'model.' in n for n in names)


def test_symlink_is_not_exported(tmp_path):
    (tmp_path/'app.py').write_text('');(tmp_path/'pyproject.toml').write_text('')
    outside=tmp_path.parent/'private-outside.txt';outside.write_text('test marker')
    (tmp_path/'docs').mkdir();(tmp_path/'docs/secret.txt').symlink_to(outside)
    with pytest.raises(ValueError,match='symlink'):packager.build_archive(tmp_path,tmp_path/'test.zip')


def test_frontend_runtime_allowlist_excludes_development_caches(tmp_path):
    for name in ['app.py','pyproject.toml','frontend/package.json','frontend/package-lock.json',
                 'frontend/src/main.jsx','frontend/src/style.css','vidhaan/web/index.html',
                 'vidhaan/web/assets/index-Abcd1234.js','vidhaan/web/assets/font-Abcd1234.woff2',
                 'frontend/node_modules/private.js','frontend/test-results/private.json',
                 'vidhaan/web/assets/secrets.txt','frontend/private.json']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('test marker')
    selected={p.relative_to(tmp_path).as_posix() for p in packager.selected_files(tmp_path)}
    assert 'vidhaan/web/assets/index-Abcd1234.js' in selected
    assert 'vidhaan/web/assets/font-Abcd1234.woff2' in selected
    assert 'frontend/src/main.jsx' in selected
    assert not any('private' in p or 'secrets' in p for p in selected)
