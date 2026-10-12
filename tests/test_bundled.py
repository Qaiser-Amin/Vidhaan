"""Fictional corpus fixtures verify offline import/privacy/integrity, not law."""
import hashlib
import json
from pathlib import Path
import httpx
import pytest
from vidhaan.bundled import load_bundle, verify_bundle
from vidhaan.registry import Registry
from vidhaan.models import Source, Domain
from vidhaan.ingestion import ingest_bytes
from vidhaan.official_sections import document_bytes, section_chunks, load_section_records, RENDERER


def make_bundle(registry, tmp_path, sections=False):
    source = Source(document_id='synthetic-bundle', title='SYNTHETIC test Act', domain=Domain.contracts,
                    namespace='official', instrument_type='Act', jurisdiction='central', official_url='https://www.incometaxindia.gov.in/synthetic-test')
    records = [{'id': '1', 'number': '1', 'locator': 'Section 1: SYNTHETIC qualification',
                'source_url': source.official_url, 'api_url': source.official_url,
                'body': 'SYNTHETIC duty applies unless the written exception is satisfied.'}]
    content = document_bytes({'metadata': {'title': source.title}, 'url': source.official_url}, records) if sections else b'SYNTHETIC duty applies unless the written exception is satisfied.\n'
    result = ingest_bytes(registry, content, 'synthetic.txt', source); source = registry.source(result.version_id)
    folder = tmp_path / 'bundle'; (folder/'documents').mkdir(parents=True); (folder/'guides').mkdir()
    (folder/'documents/synthetic.txt').write_bytes(content); (folder/'guides/original.md').write_text('SYNTHETIC original engineering guide, not legal commentary.')
    entry = {'file': 'documents/synthetic.txt', 'guide': 'guides/original.md', 'reuse_basis': 'legislation_with_original_matter', 'reuse_reference': 'SYNTHETIC fixture reference'}
    if sections:
        source.authenticity_status = 'official_sections_title_checked'
        receipt = {'renderer': RENDERER, 'receipt_mode': 'bundled-section-records-v1', 'category_id': 42,
                   'source_document_sha256': source.checksum, 'sections': records, 'acquisition_response_checksums': []}
        (folder/'sections').mkdir(); path=folder/'sections/synthetic.json'; path.write_text(json.dumps(receipt))
        source.provenance_notes = 'bundle_receipt_sha256=' + hashlib.sha256(path.read_bytes()).hexdigest()
        entry['section_receipt'] = 'sections/synthetic.json'
    entry['source'] = source.model_dump(mode='json')
    files = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
    manifest = {'schema_version': 1, 'generated_by': 'VIDHAAN selected corpus', 'files': files, 'sources': [entry]}
    (folder/'manifest.json').write_text(json.dumps(manifest))
    return folder, manifest, source


@pytest.mark.parametrize('sections', [False, True])
def test_offline_import_keeps_qualifiers_locators_and_user_review_state(registry, tmp_path, monkeypatch, sections):
    folder, manifest, source = make_bundle(registry, tmp_path, sections)
    target = Registry(tmp_path/'fresh-data')
    monkeypatch.setattr(httpx, 'Client', lambda *a, **k: (_ for _ in ()).throw(AssertionError('No network allowed')))
    assert load_bundle(target, folder)[0]['status'] == 'imported'
    version = target.versions('official')[0]
    assert version['source'].review_status == 'unreviewed' and version['source'].effective_date is None
    assert 'unless the written exception' in target.chunks(version['version_id'])[0].text
    if sections:
        records=load_section_records(version['source'],target.data_dir/version['raw_path'])
        assert all(c.locator=='Section 1: SYNTHETIC qualification' and c.page_start is None for c in target.chunks())
        assert [c.chunk_id for c in section_chunks(version['source'],records) if c.kind=='child']==[c.chunk_id for c in target.chunks()]
    target.review(version['version_id'],'reviewed','SYNTHETIC engineering review','2026-10-12');target.deactivate(version['version_id'])
    assert load_bundle(target,folder)[0]['status']=='existing'
    retained=target.versions('official')[0]
    assert retained['source'].review_status=='reviewed' and not retained['active']


@pytest.mark.parametrize('scenario', ['checksum','traversal','private','reviewed','guide','duplicate','reuse'])
def test_bad_bundle_fails_before_any_registry_import(registry, tmp_path, scenario):
    folder, manifest, source = make_bundle(registry,tmp_path)
    if scenario=='checksum':(folder/'documents/synthetic.txt').write_text('changed')
    elif scenario=='traversal':manifest['files']['../secret.txt']='0'*64
    elif scenario=='private':manifest['sources'][0]['source']['namespace']='private:session'
    elif scenario=='reviewed':manifest['sources'][0]['source']['review_status']='reviewed'
    elif scenario=='guide':manifest['sources'][0]['guide']='missing.md'
    elif scenario=='duplicate':manifest['sources'].append(manifest['sources'][0])
    else:manifest['sources'][0]['reuse_basis']='unknown'
    (folder/'manifest.json').write_text(json.dumps(manifest));target=Registry(tmp_path/'fresh-data')
    with pytest.raises(ValueError):load_bundle(target,folder)
    assert not target.versions()


def test_bundle_does_not_restore_older_source_over_user_updated_version(registry,tmp_path):
    folder,manifest,source=make_bundle(registry,tmp_path);target=Registry(tmp_path/'fresh-data')
    ingest_bytes(target,b'SYNTHETIC different, updated source body with a qualification.','updated.txt',source)
    assert load_bundle(target,folder)[0]['status']=='skipped_existing_version'
    assert len(target.versions('official'))==1


def test_compact_receipt_tampering_is_detected_even_when_body_is_unchanged(registry,tmp_path):
    folder,manifest,source=make_bundle(registry,tmp_path,True);target=Registry(tmp_path/'fresh-data');load_bundle(target,folder)
    version=target.versions('official')[0];raw=target.data_dir/version['raw_path'];path=raw.parent/'section_receipt.json'
    receipt=json.loads(path.read_text());receipt['sections'][0]['id']='forged-id';path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='receipt checksum'):load_section_records(version['source'],raw)


def test_bundle_rejects_symlinked_source(registry,tmp_path):
    folder,manifest,source=make_bundle(registry,tmp_path);path=folder/'documents/synthetic.txt';content=path.read_bytes();path.unlink()
    outside=tmp_path/'outside.txt';outside.write_bytes(content);path.symlink_to(outside)
    with pytest.raises(ValueError,match='symlink'):verify_bundle(folder)


def test_packaging_includes_only_declared_corpus_files(registry,tmp_path):
    import shutil,zipfile
    from scripts.package_project import build_archive
    folder,manifest,source=make_bundle(registry,tmp_path)
    project=tmp_path/'project';(project/'data').mkdir(parents=True)
    shutil.move(str(folder),project/'data/bundled')
    (project/'data/bundled/documents/undeclared-private.txt').write_text('PRIVATE marker must not be packaged')
    (project/'app.py').write_text('');(project/'pyproject.toml').write_text('')
    output=project/'dist/test.zip';build_archive(project,output)
    with zipfile.ZipFile(output) as archive:
        assert 'vidhaan/data/bundled/documents/synthetic.txt' in archive.namelist()
        assert 'vidhaan/data/bundled/guides/original.md' in archive.namelist()
        assert not any('undeclared-private' in name for name in archive.namelist())


def indexed_bundle(registry, tmp_path):
    from vidhaan.lexical import payload, filename
    folder, manifest, source = make_bundle(registry, tmp_path)
    local = Registry(tmp_path/'index-build'); load_bundle(local, folder)
    (folder/'indexes').mkdir(); manifest['indexes'] = []
    for domain in Domain:
        data = payload(domain, local.versions('official'), local.chunks(namespace='official'))
        name = 'indexes/' + filename(domain); (folder/name).write_text(json.dumps(data))
        manifest['files'][name] = hashlib.sha256((folder/name).read_bytes()).hexdigest()
        manifest['indexes'].append({'domain': domain.value, 'file': name, 'source_count': len(data['sources']),
                                    'chunk_count': len(data['chunk_ids']), 'signature': data['signature']})
    (folder/'manifest.json').write_text(json.dumps(manifest))
    return folder, manifest


def test_offline_portable_indexes_and_exclusions(registry, tmp_path, monkeypatch):
    from vidhaan.lexical import ensure_domain
    folder, manifest = indexed_bundle(registry, tmp_path); target = Registry(tmp_path/'loaded')
    monkeypatch.setattr(httpx, 'Client', lambda *a, **k: (_ for _ in ()).throw(AssertionError('No network')))
    load_bundle(target, folder)
    for entry in manifest['indexes']:
        data = json.loads((target.data_dir/'indexes'/Path(entry['file']).name).read_text())
        assert data['signature'] == entry['signature']
    version = target.versions('official')[0]; target.deactivate(version['version_id'])
    load_bundle(target, folder)
    tokens, report = ensure_domain(target, Domain.contracts)
    assert not tokens and report['sources'] == 0 and not target.versions('official')[0]['active']


def test_index_cannot_smuggle_an_undeclared_source(registry, tmp_path):
    folder, manifest = indexed_bundle(registry, tmp_path)
    entry = next(e for e in manifest['indexes'] if e['domain'] == Domain.contracts.value)
    path = folder/entry['file']; data = json.loads(path.read_text())
    data['sources'][0]['document_id'] = 'private-unapproved'
    path.write_text(json.dumps(data)); manifest['files'][entry['file']] = hashlib.sha256(path.read_bytes()).hexdigest()
    (folder/'manifest.json').write_text(json.dumps(manifest)); target = Registry(tmp_path/'fresh')
    with pytest.raises(ValueError, match='undeclared'): load_bundle(target, folder)
    assert not target.versions('official')


def test_new_related_scope_preserves_existing_manual_review(registry, tmp_path):
    folder, manifest, source = make_bundle(registry, tmp_path)
    target = Registry(tmp_path/'existing-project'); load_bundle(target, folder)
    version = target.versions('official')[0]
    target.review(version['version_id'], 'reviewed', 'SYNTHETIC engineering review', '2026-10-12')
    target.deactivate(version['version_id'])
    selector = 'chunk:' + target.chunks(version['version_id'])[0].chunk_id
    manifest['sources'][0]['source']['related_domain_passages'] = {Domain.family.value: [selector]}
    (folder/'manifest.json').write_text(json.dumps(manifest)); load_bundle(target, folder)
    retained = target.versions('official')[0]
    assert retained['source'].related_domain_passages[Domain.family] == [selector]
    assert retained['source'].review_status == 'reviewed'
    assert str(retained['source'].last_verification_date) == '2026-10-12' and not retained['active']
