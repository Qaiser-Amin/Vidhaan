"""Portable commands; no indexing or network downloads at import/startup."""
import argparse
import json
from pathlib import Path
import sys
from .config import ROOT, get_settings
from .models import Source, Domain, Filters
from .registry import Registry
from .ingestion import ingest_file


def emit(value):
    print(json.dumps(value,indent=2,default=str,ensure_ascii=False))


def main(argv=None):
    parser=argparse.ArgumentParser(prog='vidhaan',description='VIDHAAN local legal research')
    parser.add_argument('--profile',choices=['evidence_only','lenovo_cpu','mac_m5'],default=None)
    parser.add_argument('--data-dir',type=Path)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('diagnostics');sub.add_parser('coverage');sub.add_parser('demo');sub.add_parser('rechunk')
    download=sub.add_parser('acquire');download.add_argument('--manifest',type=Path,default=ROOT/'data/registry/source_manifest.json')
    bundled=sub.add_parser('load-bundled');bundled.add_argument('--bundle-dir',type=Path,default=ROOT/'data/bundled')
    ingestion=sub.add_parser('ingest');ingestion.add_argument('file',type=Path);ingestion.add_argument('--metadata',type=Path,required=True)
    search=sub.add_parser('search');search.add_argument('question');search.add_argument('--mode',choices=['bm25','dense','hybrid'],default='bm25')
    search.add_argument('--namespace',default='official');search.add_argument('--review-mode',choices=['demo','reviewed','synthetic'],default='demo')
    search.add_argument('--domain',choices=[d.value for d in Domain]);search.add_argument('--jurisdiction',choices=['central','state','unknown']);search.add_argument('--state');search.add_argument('--as-of');search.add_argument('--generate',action='store_true')
    index=sub.add_parser('index-dense');index.add_argument('--namespace',default='official')
    sub.add_parser('index-bm25')
    cache=sub.add_parser('cache-model');cache.add_argument('--reranker',action='store_true')
    review=sub.add_parser('review');review.add_argument('version_id');review.add_argument('--status',choices=['reviewed','unreviewed','rejected'],required=True);review.add_argument('--notes',required=True);review.add_argument('--verified-on')
    delete=sub.add_parser('delete');delete.add_argument('version_id')
    ev=sub.add_parser('evaluate');ev.add_argument('--cases',type=Path,default=ROOT/'evaluations/benchmark.json');ev.add_argument('--output',type=Path,default=ROOT/'evaluations/latest');ev.add_argument('--split',choices=['development','heldout'],default='heldout');ev.add_argument('--modes',nargs='+',default=['bm25','dense','hybrid'])
    args=parser.parse_args(argv)
    try:
        settings=get_settings(args.profile)
        if args.data_dir:
            settings=settings.model_copy(update={'data_dir':args.data_dir.resolve()}).initialize()
        registry=Registry(settings.data_dir)
        if args.command=='rechunk':
            from .chunking import chunk_pages
            from .ingestion import extract
            count=0
            for version in registry.versions():
                if version['source'].parsing_status!='parsed':continue
                path=registry.data_dir/version['raw_path']
                if version['source'].authenticity_status=='official_sections_title_checked':
                    from .official_sections import section_chunks, load_section_records
                    chunks=section_chunks(version['source'],load_section_records(version['source'],path));warnings=[]
                else:
                    pages,warnings=extract(path.read_bytes(),path.suffix.lower())
                    chunks=chunk_pages(pages,version['source'])
                registry.replace_chunks(version['version_id'],chunks,warnings);count+=1
            emit({'rechunked_versions':count,'dense_snapshots':'invalidated; rebuild explicitly'})
        elif args.command=='diagnostics':
            from .diagnostics import diagnose
            emit(diagnose(settings,registry))
        elif args.command=='coverage':emit(registry.coverage())
        elif args.command=='demo':
            source=Source(document_id='synthetic-classroom',title='SYNTHETIC classroom employment fixture',domain=Domain.employment,namespace='synthetic',jurisdiction='unknown',provenance_notes='Invented software fixture; not legal evidence')
            emit(ingest_file(registry,ROOT/'tests/fixtures/synthetic_employment.md',source).__dict__)
        elif args.command=='ingest':emit(ingest_file(registry,args.file,Source.model_validate_json(args.metadata.read_text())).__dict__)
        elif args.command=='acquire':
            from .sources import download_manifest
            log=download_manifest(registry,args.manifest);emit(log)
            if not log or any(r['status']=='failed' for r in log):return 2
        elif args.command=='load-bundled':
            from .bundled import load_bundle
            emit(load_bundle(registry,args.bundle_dir))
        elif args.command=='search':
            from .answering import ResearchService
            filters=Filters(namespace=args.namespace,review_mode=args.review_mode,domain=args.domain,jurisdiction=args.jurisdiction,state=args.state,as_of=args.as_of)
            answer=ResearchService(registry,settings).answer(args.question,filters,args.mode,args.generate)
            emit(answer.model_dump(mode='json'))
            if answer.status=='generation unavailable':return 2
        elif args.command=='index-dense':
            from .indexing import build_dense
            emit(build_dense(registry,settings,args.namespace))
        elif args.command=='index-bm25':
            from .lexical import build_all
            emit(build_all(registry))
        elif args.command=='cache-model':
            from .indexing import load_embedding
            if args.reranker:
                from sentence_transformers import CrossEncoder
                model=CrossEncoder(settings.reranker_model,device='cpu',local_files_only=False)
                emit({'cached':settings.reranker_model})
            else:
                model=load_embedding(settings.embedding_model,False,settings.embedding_revision)
                emit({'cached':settings.embedding_model,'dimension':model.get_sentence_embedding_dimension()})
        elif args.command=='review':
            registry.review(args.version_id,args.status,args.notes,args.verified_on);emit({'updated':args.version_id})
        elif args.command=='delete':registry.delete(args.version_id);emit({'deleted':args.version_id,'raw_original':'retained'})
        elif args.command=='evaluate':
            from .evaluation import evaluate
            report=evaluate(registry,settings,args.cases,args.output,args.modes,args.split)
            emit({k:v for k,v in report.items() if k!='rows'})
        return 0
    except (ValueError,OSError,RuntimeError,ImportError) as exc:
        print(f'VIDHAAN: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
