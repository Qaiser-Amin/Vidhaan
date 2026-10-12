"""Author-defined questions and passage anchors, independent of retrieval rankings.

These gold IDs identify passage locations, not certified legal or semantic support.
Run after acquisition; changing source bytes/chunker requires a new labelled benchmark.
"""
import json
import argparse
from pathlib import Path
from vidhaan.config import ROOT,get_settings
from vidhaan.registry import Registry

P='plantations-1951';B='bonded-labour-1976';C='contract-labour-rules-1971';F='labour-faq-2025-12';N='labour-faq-2026-03'
# Each tuple: split, source, question, independent exact heading/content anchor, minimum physical page.
SPEC=[
('development',P,'What passage in the Plantations source covers wholesome drinking water?','Drinking water',5),
('development',P,'Find the Plantations source discussion of canteens.','11. Canteens',5),
('development',B,'Find the Bonded Labour source provision about abolition of the bonded labour system.','4. Abolition',1),
('development',B,'What does the Bonded Labour source say about liability to repay bonded debt?','6. Liability',1),
('development',C,'Find the Contract Labour Rules passage about application for registration of establishments.','17. Manner',1),
('development',C,'Find the Contract Labour Board staff passage.','10. STAFF',1),
('development',F,'How does the December FAQ explain the definition of wages?','What does the term',1),
('development',N,'Find the additional FAQ reply about overtime allowance in the wage calculation.','Overtime allowance payment',1),
('heldout',P,'Find the Plantations provision about conservancy and sanitation.','9. Conservancy',5),
('heldout',P,'Find the Plantations provision concerning medical facilities.','10. Medical facilities',5),
('heldout',P,'Find the Plantations source passage concerning creches for workers children.','12. Creches',5),
('heldout',P,'What passage discusses educational facilities in plantations?','14. Educational',5),
('heldout',P,'Find the Plantations provision on housing facilities.','15. Housing',5),
('heldout',P,'Find the Plantations provision about weekly hours of work.','19. Weekly hours',5),
('heldout',P,'Locate the Plantations provision on recreational facilities.','13. Recreational',5),
('heldout',P,'Find the Plantations passage about welfare officers.','18. Welfare officers',5),
('heldout',B,'Locate the Bonded Labour provision on agreements or customs becoming void.','5. Agreement',1),
('heldout',B,'Find the Bonded Labour passage concerning property freed from mortgage.','7. Property',1),
('heldout',B,'Find the protection about homestead eviction in the Bonded Labour source.','8. Freed',1),
('heldout',B,'Find the Bonded Labour provision on vigilance committees.','13. Vigilance',1),
('heldout',B,'Find the functions of vigilance committees in the Bonded Labour source.','14. Functions',1),
('heldout',B,'Find the Bonded Labour provision on burden of proof.','15. Burden',1),
('heldout',B,'Find the Bonded Labour provision on abetment being an offence.','20. Abetment',1),
('heldout',C,'Find the Contract Labour Rules passage on granting a registration certificate.','18. GRANT',1),
('heldout',C,'Find the Contract Labour Rules provision on applying for a licence.','21. Application',1),
('heldout',C,'Locate Contract Labour Board meeting notice and business-list requirements.','14. NOTICE',1),
('heldout',C,'Find the Contract Labour Board quorum passage.','15. Quorum',1),
('heldout',F,'Find the December FAQ reply about leave encashment and allowances.','Whether Leave Encashment',1),
('heldout',F,'Find the December FAQ discussion about the fifty percent allowance rule.','What is the 50%',1),
('heldout',F,'Find the December FAQ passage on when gratuity is payable.','When gratuity is payable',1),
('heldout',F,'Find the December FAQ discussion of journey allowance.','Whether Journey Allowance',1),
('heldout',N,'Find the March additional FAQ passage about wage protection of white-collar employees.','wage protection of white',1),
('development','consumer-protection-2019','Find the Consumer Protection Act manner in which a complaint shall be made.','[Section 35:',0),
('heldout','consumer-protection-2019','Locate definitions in the Consumer Protection Act, 2019.','[Section 2:',0),
('heldout','consumer-protection-2019','Find the Consumer Protection Act findings of the District Commission.','[Section 39:',0),
('development','indian-contract-1872','Find compensation for loss or damage caused by breach of contract.','[Section 73:',0),
('heldout','indian-contract-1872','Find the Indian Contract Act passage on what agreements are contracts.','[Section 10:',0),
('heldout','sale-of-goods-1930','Find implied conditions as to quality or fitness in the Sale of Goods Act.','[Section 16:',0),
('development','transfer-property-1882','Find the Transfer of Property Act definition of a lease.','[Section 105:',0),
('heldout','transfer-property-1882','Find duration of certain leases in absence of written contract or local usage.','[Section 106:',0),
('heldout','rera-2016','Find the RERA passage about deposit or advance before entering into an agreement for sale.','[Section 13:',0),
('development','hindu-marriage-1955','Find the conditions for a Hindu marriage.','[Section 5:',0),
('heldout','hindu-marriage-1955','Find the Hindu Marriage Act divorce provision.','[Section 13:',0),
('heldout','hindu-succession-1956','Find devolution of interest in coparcenary property in the Hindu Succession Act.','[Section 6:',0),
('development','limitation-1963','Find the Limitation Act bar of limitation for suits, appeals and applications.','[Section 3:',0),
('heldout','limitation-1963','Find extension of the prescribed period in certain cases under the Limitation Act.','[Section 5:',0),
('heldout','bnss-2023','Find the BNSS provision on information about a cognizable offence irrespective of the area where the offence is committed.','irrespective of the area where the offence is committed',1),
('development','companies-2013','Find the Companies Act passage on incorporation of a company.','[Section 7:',0),
('heldout','companies-2013','Find the Companies Act provision for a company to have a Board of Directors.','[Section 149:',0),
('heldout','llp-2008','Find the Limited Liability Partnership Act partner as agent provision.','[Section 26:',0),
('development','information-technology-2000','Find legal recognition of electronic records in the Information Technology Act.','[Section 4:',0),
('heldout','information-technology-2000','Find the Information Technology Act penalty and compensation for damage to a computer system.','[Section 43:',0),
('heldout','environment-protection-1986','Find the Environment Protection Act provision on emissions exceeding environmental pollutant standards.','[Section 7:',0),
('heldout','employees-provident-funds-and-miscellaneous-provisions-act-1952','Find the Employees Provident Funds Act section on contributions and matters provided for in schemes.','[Section 6:',0),
('heldout','legal-metrology-act-2009','Find the Legal Metrology Act provision on declarations on pre-packaged commodities.','[Section 18:',0),
('heldout','arbitration-and-conciliation-act-1996','Find the Arbitration and Conciliation Act definition of an arbitration agreement.','[Section 7:',0),
('heldout','indian-easements-act-1882','Find the Indian Easements Act definition of an easement.','[Section 4:',0),
('heldout','hindu-adoptions-and-maintenance-act-1956','Find the Hindu Adoptions and Maintenance Act requisites of a valid adoption.','[Section 6:',0),
('heldout','advocates-act-1961','Find the Advocates Act right of advocates to practise.','[Section 30:',0),
('heldout','income-tax-act-2025','Find the Income-tax Act 2025 definition of tax year.','[Section 3:',0),
('heldout','digital-personal-data-protection-act-2023','Find the Digital Personal Data Protection Act provision requiring free specific informed consent.','[Section 6:',0),
]


def main(data_dir=None,output=None):
    registry=Registry(data_dir or get_settings().data_dir);cases=[]
    available={v['document_id'] for v in registry.versions('official') if v['active']}
    optional={F,N}
    for split,document,question,anchor,minpage in SPEC:
        versions=[v for v in registry.versions('official') if v['document_id']==document and v['active']]
        if not versions and document in optional:continue
        if len(versions)!=1:raise ValueError(f'Acquire one selected version of {document} before labelling')
        chunks=registry.chunks(versions[0]['version_id'])
        matches=[c for c in chunks if anchor.casefold() in ' '.join(c.text.split()).casefold() and (c.page_start or 0)>=minpage and c.content_role!='contents']
        if not matches:raise ValueError(f'Missing actual anchor: {document}: {anchor}')
        # The actual anchored passage is chosen before any retriever is run.
        chosen=matches[0]
        source=versions[0]['source']
        scope={'namespace':'official','review_mode':'demo'}
        if minpage==0 or document=='bnss-2023':scope.update(domain=source.domain.value,jurisdiction='central')
        cases.append({'id':f'{split}-{len(cases)+1:02d}','split':split,'question':question,
            'expected_evidence_ids':[chosen.chunk_id],'expected_document_ids':[document],
            'scope':scope,'expected_behavior':'supported',
            'provenance':f'Author-defined exact passage anchor in official-host source; {document}; {chosen.version_id}; physical page {chosen.page_start}; locator {chosen.locator}',
            'human_review':'pending','notes':'Passage-location label only; current applicability and human legal support unreviewed.'})
    behaviors=[
        ('development','Can my employer dismiss me?',{},'needs clarification'),
        ('development','Find a passage about quantum teleportation of court records.',{},'insufficient evidence'),
        ('heldout','What tenancy rules apply to my rented apartment?',{'domain':'Tenancy and property'},'needs clarification'),
        ('heldout','Am I entitled to overtime?',{},'needs clarification'),
        ('heldout','Which labour law is currently in force?',{},'needs clarification'),
        ('heldout','Find drinking water provisions as of the selected date.',{'as_of':'2026-10-12'},'insufficient evidence'),
        ('heldout','Find the consumer refund remedy in reviewed sources.',{'domain':'Consumer law','review_mode':'reviewed'},'insufficient evidence'),
        ('heldout','Find corporate tax deduction rates as of the selected date.',{'domain':'Corporate and tax','as_of':'2026-10-12'},'insufficient evidence'),
    ]
    for split,question,scope,status in behaviors:
        cases.append({'id':f'{split}-behavior-{len(cases)+1:02d}','split':split,'question':question,
            'expected_evidence_ids':[],'expected_document_ids':[],'scope':scope,'expected_behavior':status,
            'provenance':'Author-defined engineering scope/gap/clarification case; expanded corpus has unknown effective dates and zero reviewed versions.',
            'human_review':'pending'})
    expected=len(SPEC)+len(behaviors)-sum(1 for _,doc,*_ in SPEC if doc in optional and doc not in available)
    assert len(cases)==expected
    data={'schema_version':1,'corpus_signature':registry.signature('official'),
        'construction':'Questions and exact source anchors defined independently of retrieval output. Development and held-out cases are disjoint. Human semantic/legal review pending.',
        'cases':cases}
    path=Path(output or ROOT/'evaluations/benchmark.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(f'{len(cases)} cases written: {sum(c["split"]=="development" for c in cases)} development, {sum(c["split"]=="heldout" for c in cases)} held-out; actual corpus labels.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    main(args.data_dir,args.output)
