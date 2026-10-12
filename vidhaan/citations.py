"""Structural validity only: humans must still assess semantic/legal support."""
from .models import Answer, GeneratedAnswer, Hit


class CitationError(ValueError):
    pass


def validate_citations(generated: GeneratedAnswer, evidence: list[Hit]):
    known = {h.chunk.chunk_id: h for h in evidence}
    if generated.status == 'supported' and not generated.claims:
        raise CitationError('A supported generated response must contain cited claims')
    for claim in generated.claims:
        for citation in claim.citation_ids:
            if citation not in known:
                raise CitationError(f'Unknown citation: {citation}')
            if citation not in claim.quotes or not claim.quotes[citation].strip():
                raise CitationError('Each claim citation requires an exact supporting quotation')
            if claim.quotes[citation] not in known[citation].chunk.text:
                raise CitationError('Quotation is absent from the referenced exact passage')
        if set(claim.quotes) != set(claim.citation_ids):
            raise CitationError('Quote keys and citation IDs must match')
    return True


def reference(hit: Hit):
    chunk = hit.chunk
    location = chunk.locator or 'Unidentified section/paragraph'
    if chunk.page_start:
        location += f'; physical PDF page {chunk.page_start}'
        if chunk.page_end != chunk.page_start:
            location += f'–{chunk.page_end}'
    return f'{hit.source.title} — {location} — version {chunk.version_id}'


def export_markdown(answer: Answer):
    lines = ['# VIDHAAN research record', '', f'Status: {answer.status}', f'Mode: {answer.mode}',
             '', answer.text, '', '## Scope', '', str(answer.scope), '', '## Claim-to-evidence map', '']
    for claim in answer.claims:
        lines += [claim.text, 'Citations: ' + ', '.join(claim.citation_ids)]
        for cid,quote in claim.quotes.items():
            lines += [f'[{cid}]', '> ' + quote.replace('\n', '\n> '), '']
    lines += ['## Sources', '']
    for hit in answer.evidence:
        lines += [f'### [{hit.chunk.chunk_id}] {reference(hit)}',
                  f'Namespace: {hit.source.namespace}; private uploads are facts, not legal authorities.',
                  f'Review: {hit.source.review_status}; effective date: {hit.source.effective_date or "unknown"}',
                  f'URL: {hit.source.official_url or "local / unknown"}',
                  '> ' + hit.chunk.text.replace('\n', '\n> '), '']
    lines += ['## Limits', '', *answer.uncertainties,
              'A structural citation check does not establish semantic support or current law.']
    return '\n'.join(lines)
