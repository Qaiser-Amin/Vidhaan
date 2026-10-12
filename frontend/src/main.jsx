import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createPortal } from 'react-dom';
import {
  Scale, Search, Library, ChartNoAxesCombined, FlaskConical, Settings2, ArrowUpRight,
  ArrowRight, ArrowLeft, ChevronRight, ChevronDown, X, Menu, FileText, Download,
  ShieldCheck, Shield, LockKeyhole, BookOpen, SlidersHorizontal, Check, CircleHelp,
  BriefcaseBusiness, ShoppingBag, Handshake, House, Users, Gavel, Building2,
  Globe, Upload, Trash2, Plus, LoaderCircle, CircleAlert, ExternalLink, Cpu, Quote,
  Leaf, Sparkles, RefreshCw, CheckCircle2,
} from 'lucide-react';
import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/instrument-serif/latin-400.css';
import '@fontsource/instrument-serif/latin-400-italic.css';
import './style.css';

let csrf = '';
async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.method && options.method !== 'GET') headers['X-Vidhaan-CSRF'] = csrf;
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api${path}`, { ...options, headers, credentials: 'same-origin' });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join('; ') : data.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json();
}
const post = (path, data) => api(path, { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data || {}) });
const format = n => new Intl.NumberFormat('en-IN').format(n || 0);
const domainInfo = [
  { name: 'Labour and employment', short: 'Labour & employment', icon: BriefcaseBusiness, text: 'Work, wages & workplace rights', example: 'What passage covers wholesome drinking water in plantations?' },
  { name: 'Consumer law', short: 'Consumer law', icon: ShoppingBag, text: 'Consumer rights & redressal', example: 'What does the Consumer Protection Act say about unfair trade practices?' },
  { name: 'Contracts', short: 'Contracts', icon: Handshake, text: 'Agreements, obligations & remedies', example: 'What does the Indian Contract Act say about free consent?' },
  { name: 'Tenancy and property', short: 'Property & tenancy', icon: House, text: 'Ownership, transfers & real estate', example: 'What does the central Transfer of Property Act say about a lease?' },
  { name: 'Family law', short: 'Family law', icon: Users, text: 'Marriage & succession', example: 'What are the conditions for a Hindu marriage?' },
  { name: 'Criminal and civil procedure', short: 'Criminal & civil procedure', icon: Gavel, text: 'Procedure, evidence & limitation', example: 'What does the BNSS say about information in cognizable cases?' },
  { name: 'Corporate and tax', short: 'Corporate & tax', icon: Building2, text: 'Companies, partnerships & tax', example: 'What does the Companies Act say about incorporation?' },
  { name: 'Other specialist areas', short: 'Specialist areas', icon: Globe, text: 'Technology, environment & information', example: 'What does the Right to Information Act say about a request for information?' },
];
const pages = [
  { key: 'research', title: 'Legal research', label: 'Research workspace', icon: Search },
  { key: 'sources', title: 'Source library', label: 'Source library', icon: Library },
  { key: 'coverage', title: 'Corpus coverage', label: 'Corpus coverage', icon: ChartNoAxesCombined },
  { key: 'evaluation', title: 'Evaluation', label: 'Evaluation', icon: FlaskConical },
  { key: 'settings', title: 'Workspace settings', label: 'Workspace settings', icon: Settings2 },
];
const initialFilters = { domain: '', corpus: 'demo', jurisdiction: '', state: '', as_of: '', version_ids: [], include_superseded: false, retrieval: 'bm25', generate: false, compare_private: false };
const collection = f => f === 'private' ? 'private' : f === 'synthetic' ? 'synthetic' : 'official';
function Button({ children, icon: Icon, className = '', ...props }) {
  return <button className={`button ${className}`} {...props}>{Icon && <Icon size={16} className={Icon === LoaderCircle ? 'spin' : undefined} aria-hidden="true" />}{children}</button>;
}
function IconButton({ icon: Icon, label, ...props }) {
  return <button className="icon-button" aria-label={label} title={label} {...props}><Icon size={19} aria-hidden="true" /></button>;
}
function Select({ label, children, className = '', ...props }) {
  return <label className={`field ${className}`}><span>{label}</span><span className="select-wrap"><select {...props}>{children}</select><ChevronDown size={14} aria-hidden="true" /></span></label>;
}
function Badge({ children, tone = '' }) { return <span className={`badge ${tone}`}>{children}</span>; }
function Notice({ children, error = false }) {
  return <div className={`notice ${error ? 'notice-error' : ''}`} role={error ? 'alert' : undefined}><CircleAlert size={17} aria-hidden="true" /><div>{children}</div></div>;
}
function Empty({ title, children, icon: Icon = BookOpen }) {
  return <div className="empty"><div className="empty-icon"><Icon size={25} /></div><h3>{title}</h3><p>{children}</p></div>;
}
function Dialog({ title, eyebrow, children, onClose, wide = false }) {
  const ref = useRef();
  useEffect(() => {
    const old = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    ref.current.focus();
    const handle = e => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab') {
        const items = [...ref.current.querySelectorAll('button, a[href], input, textarea, select, [tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
        const first = items[0], last = items.at(-1);
        if (!items.length) { e.preventDefault(); return; }
        if (e.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', handle);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', handle); old?.focus(); };
  }, [onClose]);
  return createPortal(<div className="dialog-overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}><section ref={ref} tabIndex={-1} className={`drawer ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby="dialog-title"><header className="drawer-head"><div><span className="eyebrow">{eyebrow}</span><h2 id="dialog-title">{title}</h2></div><IconButton icon={X} label="Close reader" onClick={onClose} /></header><div className="drawer-body">{children}</div></section></div>, document.body);
}
function LegalIllustration() {
  return <div className="legal-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="art-spark spark-one">✦</div><div className="art-spark spark-two">✧</div><div className="folio-back" /><div className="folio"><span className="folio-caption">THE EVIDENCE COLLECTION</span><Scale className="folio-scales" size={63} strokeWidth={1} /><div className="folio-line" /><div className="folio-line short" /><span className="folio-seal"><Leaf size={19} /></span></div><span className="art-tag"><ShieldCheck size={14} /> Trace every source</span></div>;
}

function App() {
  const [boot, setBoot] = useState(null), [fatal, setFatal] = useState('');
  const [page, setPage] = useState('research'), [mobileNav, setMobileNav] = useState(false);
  const [filters, setFilters] = useState(initialFilters), [profile, setProfile] = useState('evidence_only');
  const [question, setQuestion] = useState(''), [answer, setAnswer] = useState(null), [asked, setAsked] = useState('');
  const [searching, setSearching] = useState(false), [error, setError] = useState(''), [toast, setToast] = useState('');
  const [refine, setRefine] = useState(false), [scopeSources, setScopeSources] = useState([]), [reader, setReader] = useState(null);
  const searchRef = useRef(), answerRef = useRef(), requestRef = useRef(null);
  const refresh = useCallback(async () => {
    const result = await api('/bootstrap'); csrf = result.csrf; setBoot(result); return result;
  }, []);
  useEffect(() => { refresh().then(b => setProfile(b.profile)).catch(e => setFatal(e.message)); }, [refresh]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(''), 4500); return () => clearTimeout(t); }, [toast]);
  useEffect(() => {
    requestRef.current?.abort(); setSearching(false); setAnswer(null); setError('');
    if (boot) api(`/sources?scope=${collection(filters.corpus)}`).then(setScopeSources).catch(e => setError(e.message));
  }, [filters, profile, boot?.revision]);
  const update = values => setFilters(f => ({ ...f, ...values }));
  const navigate = key => { setPage(key); setMobileNav(false); window.scrollTo({ top: 0, behavior: 'instant' }); };
  const closeReader = useCallback(() => setReader(null), []);
  const changed = async message => { setAnswer(null); await refresh(); if (message) setToast(message); };
  async function research(e) {
    e?.preventDefault(); if (!question.trim() || searching) return;
    requestRef.current?.abort(); const controller = new AbortController(); requestRef.current = controller;
    setSearching(true); setAnswer(null); setError(''); setAsked(question.trim());
    try {
      const data = await api('/research', { method: 'POST', signal: controller.signal, body: JSON.stringify({
        ...filters, question: question.trim(), profile, domain: filters.domain || null,
        jurisdiction: filters.jurisdiction || null, state: filters.state || null, as_of: filters.as_of || null,
      }) });
      if (controller.signal.aborted) return;
      setAnswer(data);
      setTimeout(() => answerRef.current?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' }), 100);
    } catch (e) { if (e.name !== 'AbortError') setError(e.message); }
    finally { if (!controller.signal.aborted) setSearching(false); }
  }
  const example = d => {
    update({ domain: d.name, jurisdiction: d.name === 'Tenancy and property' ? 'central' : filters.jurisdiction });
    setQuestion(d.example); navigate('research'); setTimeout(() => searchRef.current?.focus(), 30);
  };
  if (fatal) return <div className="boot-error"><Scale size={32} /><h1>Workspace unavailable</h1><p>{fatal}</p><Button onClick={() => location.reload()} icon={RefreshCw}>Retry connection</Button></div>;
  if (!boot) return <div className="boot-loading"><Scale size={40} strokeWidth={1.2} /><span>Opening your workspace</span><LoaderCircle className="spin" size={19} /></div>;
  const activePage = pages.find(p => p.key === page);
  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    {mobileNav && <div className="nav-backdrop" onClick={() => setMobileNav(false)} />}
    <aside className={`sidebar ${mobileNav ? 'is-open' : ''}`} aria-label="Workspace navigation">
      <button className="brand" onClick={() => navigate('research')} aria-label="VIDHAAN home"><span className="brand-mark"><Scale size={25} strokeWidth={1.4} /></span><span><strong>VIDHAAN<span className="brand-dot">.</span></strong><small>THE LEGAL RESEARCH WORKSPACE</small></span></button>
      <div className="sidebar-rule" /><span className="nav-label">YOUR WORKSPACE</span>
      <nav>{pages.filter(p => p.key !== 'settings').map(p => <button key={p.key} className={`nav-item ${page === p.key ? 'active' : ''}`} onClick={() => navigate(p.key)} aria-current={page === p.key ? 'page' : undefined}><p.icon size={19} strokeWidth={1.7} /><span>{p.label}</span>{page === p.key && <span className="nav-dot" />}</button>)}</nav>
      <div className="sidebar-note"><span className="small-icon"><BookOpen size={17} /></span><span className="eyebrow">A LIBRARY WITH CONTEXT</span><p>Every answer starts<br />with a source you can read.</p><div className="sidebar-count"><span>{boot.coverage.filter(r => r.indexed).length} / 8 domains indexed</span><ArrowUpRight size={14} /></div><div className="mini-progress"><span style={{ width: `${boot.coverage.filter(r => r.indexed).length / 8 * 100}%` }} /></div><button className="text-link" onClick={() => navigate('coverage')}>Explore coverage <ChevronRight size={13} /></button></div>
      <div className="sidebar-bottom"><button className={`nav-item ${page === 'settings' ? 'active' : ''}`} onClick={() => navigate('settings')}><Settings2 size={18} /><span>Workspace settings</span></button><div className="local-status"><span className="status-dot" /><div><strong>Local workspace</strong><small>Your files stay on this machine</small></div><LockKeyhole size={14} /></div><div className="author"><span className="avatar">QA</span><div><strong>University project</strong><small>Qaiser Amin Ganaie</small></div><span className="version">v1.0</span></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb"><span className="mobile-menu"><IconButton icon={Menu} label="Open navigation" onClick={() => setMobileNav(true)} /></span><span>Workspace</span><ChevronRight size={13} /><strong>{activePage.title}</strong></div><div className="topbar-right"><span className="topbar-status"><span className="status-dot" /> Local evidence</span><IconButton icon={CircleHelp} label="About this workspace" onClick={() => setReader({ type: 'about' })} /></div></header>
    <main id="main-content" className="main-content">
      <div key={page} className="page-enter">
      {page === 'research' && <>
        <section className="research-hero"><div><span className="eyebrow hero-eyebrow"><span className="tiny-line" /> EVIDENCE FIRST. ALWAYS.</span><h1>A clearer path<br />through <em>Indian law.</em></h1><p>Ask a question. Explore the source.<br className="desktop-break" /> Build your research on evidence you can see.</p></div><LegalIllustration /></section>
        <form className={`research-box ${searching ? 'is-searching' : ''}`} onSubmit={research}>
          <div className="research-box-head"><label htmlFor="research-question"><Search size={17} /> What would you like to research?</label><span className="keyboard-hint">Ctrl / ⌘ + Enter</span></div>
          <textarea ref={searchRef} id="research-question" value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') research(e); }} maxLength={2000} rows={3} placeholder="Ask about a law, explore a provision, or search a legal question…" disabled={searching} />
          <div className="research-box-footer"><div className="inline-scopes"><label className="scope-select"><Globe size={14} /><select aria-label="Legal domain" value={filters.domain} disabled={searching} onChange={e => update({ domain: e.target.value })}><option value="">All legal domains</option>{domainInfo.map(d => <option key={d.name} value={d.name}>{d.short}</option>)}</select><ChevronDown size={13} /></label><label className="scope-select"><BookOpen size={14} /><select aria-label="Research collection" value={filters.corpus} disabled={searching} onChange={e => update({ corpus: e.target.value, version_ids: [], retrieval: e.target.value === 'private' ? 'bm25' : filters.retrieval, generate: false })}><option value="demo">Official sources · demo</option><option value="reviewed">Reviewed sources</option><option value="private">Private documents</option><option value="synthetic">Synthetic fixture</option></select><ChevronDown size={13} /></label></div><Button type="submit" className="primary search-button" disabled={!question.trim() || searching}>{searching ? <><LoaderCircle size={16} className="spin" /> Searching evidence</> : <>Find evidence <ArrowUpRight size={17} /></>}</Button></div>
        </form>
        <div className="search-under"><span><ShieldCheck size={14} /> {filters.corpus === 'demo' ? 'Unreviewed sources · applicability remains unknown' : filters.corpus === 'reviewed' ? 'Only manually reviewed, dated versions' : filters.corpus === 'private' ? 'Uploaded facts · not legal authorities' : 'Invented classroom material · not Indian law'}</span><button className={`text-link refine-toggle ${refine ? 'selected' : ''}`} onClick={() => setRefine(!refine)} aria-expanded={refine}><SlidersHorizontal size={14} /> Refine scope <ChevronDown size={13} /></button></div>
        {refine && <section className="refine-panel expand-enter"><div className="filter-grid"><Select label="Jurisdiction" value={filters.jurisdiction} onChange={e => update({ jurisdiction: e.target.value })}><option value="">Any recorded scope</option><option value="central">Central</option><option value="state">State</option></Select><label className="field"><span>State or union territory</span><input placeholder="Exact registered name" value={filters.state} onChange={e => update({ state: e.target.value })} maxLength={100} /></label><label className="field"><span>Research as of a date</span><input type="date" value={filters.as_of} onChange={e => update({ as_of: e.target.value })} /></label><Select label="Retrieval method" value={filters.retrieval} onChange={e => update({ retrieval: e.target.value })}><option value="bm25">BM25 · available offline</option><option value="dense" disabled={filters.corpus === 'private'}>Dense · needs a local index</option><option value="hybrid" disabled={filters.corpus === 'private'}>Hybrid · needs a local index</option></Select></div>
          <label className="field version-picker"><span>Source versions <small>Leave empty to search eligible versions</small></span><select multiple size={3} value={filters.version_ids} onChange={e => update({ version_ids: [...e.target.selectedOptions].map(o => o.value) })}>{scopeSources.map(v => <option key={v.version_id} value={v.version_id}>{v.source.title} · {v.version_id}</option>)}</select></label>
          <div className="filter-checks"><label><input type="checkbox" checked={filters.include_superseded} onChange={e => update({ include_superseded: e.target.checked })} /> Include superseded versions</label><label><input type="checkbox" checked={filters.compare_private} onChange={e => update({ compare_private: e.target.checked })} /> Compare a private clause with official evidence</label><label><input type="checkbox" checked={filters.generate} disabled={profile === 'evidence_only' || !['demo', 'reviewed'].includes(filters.corpus)} onChange={e => update({ generate: e.target.checked })} /> Use local Ollama generation</label></div><div className="refine-bottom"><span>Unknown effective dates are excluded from dated research. {profile === 'evidence_only' && 'Enable a local model profile in settings for generation.'}</span><button className="text-link" onClick={() => setFilters(initialFilters)}>Reset filters</button></div></section>}
        {error && <Notice error>{error}</Notice>}
        {searching && <div className="search-loading" role="status"><span className="loading-orb"><Search size={20} /></span><div><strong>Looking through the selected sources</strong><p>Finding eligible passages and checking their references…</p></div><div className="loading-dots"><i /><i /><i /></div></div>}
        {answer && <section ref={answerRef} className="results-section"><ResearchResults answer={answer} asked={asked} onRead={hit => setReader({ type: 'evidence', hit })} /></section>}
        {!answer && !searching && <>
          <div className="try-row"><span>TRY A QUESTION</span><button onClick={() => example(domainInfo[1])}>Consumer protection <ArrowUpRight size={12} /></button><button onClick={() => example(domainInfo[2])}>Free consent in contracts <ArrowUpRight size={12} /></button><button onClick={() => example(domainInfo[4])}>Hindu marriage conditions <ArrowUpRight size={12} /></button></div>
          <section className="domains-section"><div className="section-heading"><div><span className="eyebrow">FIND YOUR STARTING POINT</span><h2>Explore a legal domain</h2></div><button className="text-link" onClick={() => navigate('sources')}>Browse all sources <ArrowRight size={15} /></button></div><div className="domain-grid">{domainInfo.map((d, i) => { const row = boot.coverage.find(r => r.domain === d.name); return <button key={d.name} className={`domain-card ${filters.domain === d.name ? 'chosen' : ''}`} style={{ '--delay': `${i * 35}ms` }} onClick={() => example(d)}><span className={`domain-icon color-${i % 4}`}><d.icon size={20} strokeWidth={1.5} /></span><ArrowUpRight className="domain-arrow" size={17} /><h3>{d.short}</h3><p>{d.text}</p><span className="domain-count">{row?.indexed || 0} indexed {row?.indexed === 1 ? 'source' : 'sources'}</span></button>; })}</div></section>
          <section className="evidence-strip"><div className="evidence-strip-icon"><Quote size={23} strokeWidth={1.4} /></div><div><h3>Good research leaves a trail.</h3><p>Exact passages, source links, and visible review status. Every step is yours to inspect.</p></div><button className="text-link" onClick={() => setReader({ type: 'about' })}>How it works <ArrowUpRight size={14} /></button></section>
        </>}
      </>}
      {page === 'sources' && <SourceLibrary boot={boot} changed={changed} onRead={v => setReader({ type: 'source', versionId: v.version_id })} onUpload={() => setReader({ type: 'upload' })} />}
      {page === 'coverage' && <Coverage boot={boot} onDomain={example} />}
      {page === 'evaluation' && <Evaluation />}
      {page === 'settings' && <WorkspaceSettings boot={boot} profile={profile} setProfile={v => { setProfile(v); update({ generate: false }); }} changed={changed} />}
      </div>
      <footer className="workspace-footer"><span><Scale size={13} /> VIDHAAN · Evidence-first Indian legal research</span><span>Research aid. Verify applicability with a qualified professional.</span></footer>
    </main></div>
    {toast && <div className="toast" role="status"><CheckCircle2 size={18} />{toast}<IconButton icon={X} label="Dismiss notification" onClick={() => setToast('')} /></div>}
    {reader?.type === 'evidence' && <EvidenceReader hit={reader.hit} onClose={closeReader} />}
    {reader?.type === 'source' && <SourceReader versionId={reader.versionId} onClose={closeReader} changed={changed} />}
    {reader?.type === 'upload' && <UploadDialog onClose={closeReader} changed={changed} />}
    {reader?.type === 'about' && <Dialog title="Research you can inspect." eyebrow="THE VIDHAAN APPROACH" onClose={closeReader}><div className="about-hero"><Scale size={40} strokeWidth={1.2} /><p>Follow the evidence.<br /><em>Keep the unknowns visible.</em></p></div><div className="about-steps">{[['01', 'Choose your scope', 'Select a domain, jurisdiction, date, and source collection. Official, synthetic, and private documents stay separate.'], ['02', 'Read the source', 'Search retrieves exact passages. Inspect their full section, physical PDF pages where available, original file, and provenance.'], ['03', 'Keep a research record', 'Export references and quotations. Matching evidence does not certify legal correctness or current applicability.']].map(([n, h, p]) => <div key={n}><span>{n}</span><div><h3>{h}</h3><p>{p}</p></div></div>)}</div><Notice>This university prototype has incomplete coverage. Imported sources are unreviewed until a person records a version-specific review. Private files stay locally and can be cleared explicitly.</Notice><p className="muted">Created by Qaiser Amin Ganaie. No paid research service is required.</p></Dialog>}
  </div>;
}

function ResearchResults({ answer, asked, onRead }) {
  const generated = answer.mode === 'Ollama structured generation';
  const [exportError, setExportError] = useState('');
  async function download(kind) {
    setExportError('');
    try {
      const response = await fetch(`/api/exports/${answer.answer_id}?format=${kind}`);
      if (!response.ok) throw new Error((await response.json()).detail);
      const url = URL.createObjectURL(await response.blob()); const a = document.createElement('a');
      a.href = url; a.download = `vidhaan_research.${kind === 'json' ? 'json' : 'md'}`; a.click(); URL.revokeObjectURL(url);
    } catch (e) { setExportError(e.message); }
  }
  return <><div className="section-heading result-heading"><div><span className="eyebrow">YOUR RESEARCH RECORD</span><h2>{answer.evidence.length ? `${answer.evidence.length} passages to explore` : 'A closer look is needed'}</h2></div><div className="result-actions"><Button icon={Download} onClick={() => download('markdown')}>Markdown</Button><Button icon={Download} onClick={() => download('json')}>JSON</Button></div></div><p className="asked-question">“{asked}”</p><div className="result-meta"><Badge tone={answer.status === 'supported' ? 'green' : 'amber'}>{answer.status === 'supported' ? 'Matching evidence found' : answer.status}</Badge><span>{answer.mode}</span><span>{answer.metrics?.retrieval_backend || 'BM25'}</span>{answer.timings?.total_wall_seconds != null && <span>{answer.timings.total_wall_seconds.toFixed(2)}s</span>}</div>
    {(generated || !answer.evidence.length) && <div className="answer-text">{answer.text}</div>}
    {answer.mode === 'uploaded clause + legal evidence' && <Notice>Possible issue requiring human review. Private extracts are uploaded facts; the linked official passages do not establish a definite legal conclusion.</Notice>}
    {answer.missing_facts?.length > 0 && <div className="missing-facts"><h3>Details needed</h3>{answer.missing_facts.map((s, i) => <p key={i}>{s}</p>)}</div>}
    {exportError && <Notice error>{exportError}</Notice>}
    <div className="evidence-list">{answer.evidence.map((hit, i) => <article key={hit.chunk.chunk_id} className="evidence-card" style={{ '--delay': `${i * 50}ms` }}><div className="evidence-card-top"><span className="citation-number">{String(i + 1).padStart(2, '0')}</span><div><span className="source-kicker">{hit.source.namespace.startsWith('private:') ? 'PRIVATE DOCUMENT · FACTS' : hit.source.namespace === 'synthetic' ? 'SYNTHETIC · NOT LAW' : hit.source.domain}</span><h3>{hit.source.title}</h3></div><Badge tone={hit.source.review_status === 'reviewed' ? 'green' : 'amber'}>{hit.source.review_status}</Badge></div><div className="evidence-location"><span>{hit.chunk.locator || 'Unidentified passage'}</span>{hit.chunk.page_start && <span>Physical PDF p. {hit.chunk.page_start}{hit.chunk.page_end !== hit.chunk.page_start ? `–${hit.chunk.page_end}` : ''}</span>}<span>Effective date: {hit.source.effective_date || 'unknown'}</span></div><blockquote>{hit.chunk.text}</blockquote><div className="evidence-card-bottom"><span><Shield size={13} /> Scope: {hit.chunk.jurisdiction}</span><button className="text-link" onClick={() => onRead(hit)}>Read full context <ArrowUpRight size={15} /></button></div></article>)}</div>
    {generated && <details className="details-panel"><summary>Claim-to-evidence map <ChevronDown size={15} /></summary>{answer.claims.map((c, i) => <div key={i} className="claim"><p>{c.text}</p>{Object.entries(c.quotes).map(([id, text]) => <div key={id}><code>{id}</code><blockquote>{text}</blockquote></div>)}</div>)}</details>}
    {answer.uncertainties?.length > 0 && <details className="details-panel" open><summary>Research limits & uncertainties <ChevronDown size={15} /></summary><ul>{answer.uncertainties.map((s, i) => <li key={i}>{s}</li>)}</ul></details>}
  </>;
}

function EvidenceReader({ hit, onClose }) {
  const [data, setData] = useState(null), [error, setError] = useState('');
  useEffect(() => { let active = true; api(`/chunks/${hit.chunk.chunk_id}`).then(d => active && setData(d)).catch(e => active && setError(e.message)); return () => { active = false; }; }, [hit]);
  const pagination = hit.chunk.page_start ? `Physical PDF pages ${hit.chunk.page_start}–${hit.chunk.page_end}. Printed pagination unknown.` : 'Text collection · PDF pagination does not apply.';
  return <Dialog title={hit.source.title} eyebrow="EVIDENCE READER" onClose={onClose} wide><div className="reader-badges"><Badge tone="amber">{hit.source.review_status}</Badge><Badge>{hit.chunk.locator || 'Unidentified passage'}</Badge><Badge>{hit.source.namespace.startsWith('private:') ? 'Private facts' : hit.source.namespace}</Badge></div><div className="reader-actions"><a className="button" href={`/api/sources/${hit.chunk.version_id}/download`}><Download size={15} /> Local source file</a>{data?.section_url && <a className="button" href={data.section_url} target="_blank" rel="noopener noreferrer"><ExternalLink size={15} /> Department section</a>}{data?.official_link && <a className="button" href={data.official_link} target="_blank" rel="noopener noreferrer"><ExternalLink size={15} /> Official source</a>}</div><div className="passage-meta reader-location">{pagination}</div><Notice>Effective date: {hit.source.effective_date || 'unknown'}. Review and applicability must be established separately from the exact text.</Notice><h3 className="reader-section-title">Retrieved passage</h3><div className="legal-text">{hit.chunk.text}</div>{error && <Notice error>{error}</Notice>}{!data && !error && <div className="inline-loading"><LoaderCircle className="spin" size={18} /> Loading full section…</div>}{data?.parent && data.parent.text !== hit.chunk.text && <><h3 className="reader-section-title">Surrounding section</h3><div className="legal-text context-text">{data.parent.text}</div></>}<Metadata source={hit.source} chunk={hit.chunk} />{hit.source.extraction_warnings.map((w, i) => <Notice key={i}>{w}</Notice>)}</Dialog>;
}
function Metadata({ source, chunk }) {
  return <div className="metadata"><h3>Source provenance</h3><dl>{[
    ['Domain', source.domain], ['Authority', source.issuing_authority || 'unknown'], ['Instrument', source.instrument_type || 'unknown'],
    ['Jurisdiction', chunk?.jurisdiction || source.jurisdiction], ...(chunk ? [['Physical PDF pages', chunk.page_start ? `${chunk.page_start}–${chunk.page_end}` : 'not applicable'], ['Printed pagination', 'unknown']] : []), ['Publication date', source.publication_date || 'unknown'],
    ['Effective date', source.effective_date || 'unknown'], ['Retrieved', source.retrieved_at || 'unknown'],
    ['Verification date', source.last_verification_date || 'not recorded'], ['Authenticity check', source.authenticity_status],
    ['Version', chunk?.version_id || source.source_version], ['SHA-256', source.checksum || 'unknown'],
  ].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>{source.provenance_notes && <details className="details-panel"><summary>Acquisition notes <ChevronDown size={14} /></summary><p className="pre-wrap">{source.provenance_notes}</p></details>}</div>;
}

function PageHeading({ eyebrow, title, description, children }) { return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{children}</div>; }
function SourceLibrary({ boot, changed, onRead, onUpload }) {
  const [scope, setScope] = useState('official'), [sources, setSources] = useState(null), [query, setQuery] = useState(''), [domain, setDomain] = useState(''), [error, setError] = useState('');
  useEffect(() => { let live = true; setSources(null); api(`/sources?scope=${scope}`).then(d => live && setSources(d)).catch(e => live && setError(e.message)); return () => { live = false; }; }, [scope, boot.revision]);
  const filtered = (sources || []).filter(v => (!domain || v.source.domain === domain || v.source.related_domain_passages?.[domain]?.length) && (v.source.title + ' ' + v.source.domain).toLowerCase().includes(query.toLowerCase()));
  return <><PageHeading eyebrow="YOUR RESEARCH FOUNDATION" title="The source library." description="Read the originals. Know the version. See what has been reviewed."><Button className="primary" icon={Plus} onClick={onUpload}>Add private document</Button></PageHeading><div className="stats-row"><Stat label="Official sources" value={boot.totals.sources} icon={Library} /><Stat label="Indexed passages" value={format(boot.totals.passages)} icon={FileText} /><Stat label="Reviewed versions" value={boot.totals.reviewed} icon={ShieldCheck} /><Stat label="Your private files" value={boot.private_sources} icon={LockKeyhole} /></div>
    <div className="library-toolbar"><div className="segmented" aria-label="Source collections">{[['official', 'Official sources'], ['private', 'Private documents'], ['synthetic', 'Synthetic fixture']].map(([key, label]) => <button key={key} className={scope === key ? 'active' : ''} onClick={() => setScope(key)} aria-pressed={scope === key}>{label}</button>)}</div><div className="library-controls"><label className="search-field"><Search size={16} /><input aria-label="Search sources" value={query} onChange={e => setQuery(e.target.value)} placeholder="Find a source…" /></label><Select label="Filter sources by domain" className="visually-labeled" value={domain} onChange={e => setDomain(e.target.value)}><option value="">All domains</option>{domainInfo.map(d => <option key={d.name} value={d.name}>{d.short}</option>)}</Select></div></div>
    {scope !== 'official' && <Notice>{scope === 'private' ? 'Only this browser session’s uploads appear here. They are local facts, not legal authorities. Clear them in workspace settings.' : 'These invented fixtures test the software pipeline. They do not describe Indian law.'}</Notice>}{error && <Notice error>{error}</Notice>}
    {!sources ? <div className="inline-loading"><LoaderCircle className="spin" size={19} /> Opening the collection…</div> : !filtered.length ? <Empty title={sources.length ? 'No sources match your search' : 'This collection is empty'}>{sources.length ? 'Try a different title or legal domain.' : scope === 'private' ? 'Add a PDF, TXT or Markdown document to begin a private search.' : 'Use workspace settings to load the included corpus or the clearly labelled synthetic fixture.'}</Empty> : <div className="source-table"><div className="source-table-head"><span>DOCUMENT & DOMAIN</span><span>REVIEW STATUS</span><span>SCOPE</span><span /></div>{filtered.map((v, i) => <button key={v.version_id} className="source-row" onClick={() => onRead(v)} style={{ '--delay': `${Math.min(i, 8) * 25}ms` }}><span className="source-name"><span className="file-icon"><FileText size={20} strokeWidth={1.4} /></span><span><strong>{v.source.title}</strong><small>{v.source.domain}{Object.keys(v.source.related_domain_passages || {}).length > 0 && ' · selected passages also in Family law'}{!v.active && ' · excluded'}{!v.indexed && ' · no indexed text'}</small></span></span><span><Badge tone={v.source.review_status === 'reviewed' ? 'green' : 'amber'}>{v.source.review_status}</Badge></span><span className="table-scope">{v.source.jurisdiction}<small>Effective date {v.source.effective_date || 'unknown'}</small></span><ArrowUpRight size={17} /></button>)}</div>}
    <p className="library-count">{filtered.length} {filtered.length === 1 ? 'version' : 'versions'} shown · original files and version-specific metadata</p><div className="subtle-note"><ShieldCheck size={17} /><p>Collected, indexed, and reviewed are different states. An official-host source is not automatically verified as current law.</p></div></>;
}

function SourceReader({ versionId, onClose, changed }) {
  const [data, setData] = useState(null), [tab, setTab] = useState('text'), [passages, setPassages] = useState(null);
  const [query, setQuery] = useState(''), [offset, setOffset] = useState(0), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [review, setReview] = useState({ status: 'unreviewed', notes: '', verified_on: '' }), [confirmExclude, setConfirmExclude] = useState(false);
  const loadDetail = useCallback(() => api(`/sources/${versionId}`).then(d => { setData(d); setReview({ status: d.source.review_status, notes: d.source.reviewer_notes || '', verified_on: d.source.last_verification_date || '' }); }), [versionId]);
  useEffect(() => { let live = true; loadDetail().catch(e => live && setError(e.message)); return () => { live = false; }; }, [loadDetail]);
  useEffect(() => { let live = true; setPassages(null); api(`/sources/${versionId}/passages?offset=${offset}&query=${encodeURIComponent(query)}`).then(d => live && setPassages(d)).catch(e => live && setError(e.message)); return () => { live = false; }; }, [versionId, offset, query]);
  async function mutate(action, body) {
    setBusy(true); setError('');
    try { await post(`/sources/${versionId}/${action}`, body); await changed(action === 'review' ? 'Version-specific review recorded.' : 'Source excluded from active research.'); await loadDetail(); setConfirmExclude(false); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <Dialog title={data?.source.title || 'Opening source…'} eyebrow="SOURCE READER" onClose={onClose} wide>{error && <Notice error>{error}</Notice>}{data && <><div className="reader-badges"><Badge tone="amber">{data.source.review_status}</Badge><Badge tone={data.active ? 'green' : ''}>{data.active ? 'Active version' : 'Excluded version'}</Badge><Badge>{data.child_count} indexed passages</Badge></div><div className="reader-actions"><a className="button" href={`/api/sources/${versionId}/download`}><Download size={15} /> Download original</a>{data.official_link && <a className="button" href={data.official_link} target="_blank" rel="noopener noreferrer"><ExternalLink size={15} /> Official source</a>}</div><div className="reader-tabs">{[['text', 'Document text'], ['metadata', 'Provenance'], ...(data.source.namespace === 'official' ? [['review', 'Manual review']] : [])].map(([k, label]) => <button key={k} onClick={() => setTab(k)} className={tab === k ? 'active' : ''} aria-pressed={tab === k}>{label}</button>)}</div>
    {tab === 'text' && <><label className="search-field passage-search"><Search size={15} /><input value={query} onChange={e => { setQuery(e.target.value); setOffset(0); }} placeholder="Find text or a section…" aria-label="Search document sections" /></label>{!passages ? <div className="inline-loading"><LoaderCircle className="spin" size={18} /> Loading sections…</div> : !passages.items.length ? <Empty title="No extracted sections">{query ? 'Try another word or section label.' : 'This document may need OCR. The original remains available.'}</Empty> : <>{passages.items.map(c => <details className="section-passage" key={c.chunk_id}><summary><span>{c.locator || 'Front matter / unidentified paragraph'}</span><ChevronDown size={16} /></summary><div className="passage-meta">{c.page_start ? `Physical PDF pages ${c.page_start}–${c.page_end}. Printed pagination unknown.` : 'Text collection · PDF pagination does not apply.'} Scope: {c.jurisdiction}</div><div className="legal-text">{c.text}</div></details>)}<div className="pagination"><Button icon={ArrowLeft} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 12))}>Previous</Button><span>{offset + 1}–{Math.min(offset + 12, passages.total)} of {passages.total} sections</span><Button disabled={offset + 12 >= passages.total} onClick={() => setOffset(offset + 12)}>Next <ArrowRight size={14} /></Button></div></>}</>}
    {tab === 'metadata' && <><Metadata source={data.source} /><h3 className="reader-section-title">Extraction notes</h3>{data.source.extraction_warnings.length ? data.source.extraction_warnings.map((w, i) => <Notice key={i}>{w}</Notice>) : <p className="muted">No extraction warnings recorded. This does not establish legal completeness.</p>}</>}
    {tab === 'review' && <form className="review-form" onSubmit={e => { e.preventDefault(); mutate('review', { ...review, verified_on: review.verified_on || null }); }}><Notice>Record an actual human review of this exact version. A reviewed version also needs a verification date to qualify for reviewed research. Recording review does not fill unknown effective dates.</Notice><Select label="Manual review status" value={review.status} onChange={e => setReview({ ...review, status: e.target.value })}><option value="unreviewed">Unreviewed</option><option value="reviewed">Reviewed</option><option value="rejected">Rejected</option></Select><label className="field"><span>Reviewer, scope, method & unresolved issues</span><textarea value={review.notes} onChange={e => setReview({ ...review, notes: e.target.value })} required rows={5} maxLength={5000} placeholder="Record version-specific review notes…" /></label><label className="field"><span>Established verification date <small>Optional when unknown</small></span><input type="date" value={review.verified_on} onChange={e => setReview({ ...review, verified_on: e.target.value })} /></label><Button type="submit" className="primary" icon={busy ? LoaderCircle : Check} disabled={busy}>Record manual review</Button></form>}
    <div className="reader-exclusion">{data.active && (confirmExclude ? <><p>Exclude this version from active searches? Its original and history will be retained.</p><div className="reader-actions"><Button className="danger" disabled={busy} onClick={() => mutate('exclude')}>Exclude version</Button><Button onClick={() => setConfirmExclude(false)}>Keep active</Button></div></> : <button className="text-link danger-text" onClick={() => setConfirmExclude(true)}>Exclude version from active research</button>)}</div></>}</Dialog>;
}

function UploadDialog({ onClose, changed }) {
  const [file, setFile] = useState(null), [domain, setDomain] = useState(domainInfo[0].name), [error, setError] = useState(''), [busy, setBusy] = useState(false), [done, setDone] = useState(null), [drag, setDrag] = useState(false);
  function choose(value) {
    setError(''); setDone(null);
    if (value && (value.size > 25 * 1024 * 1024 || !/\.(pdf|txt|md)$/i.test(value.name))) { setError('Choose a PDF, TXT or Markdown file up to 25 MiB.'); return; }
    setFile(value);
  }
  async function upload(e) {
    e.preventDefault(); if (!file) return; setBusy(true); setError('');
    const form = new FormData(); form.append('file', file); form.append('domain', domain);
    try { const result = await post('/private/upload', form); setDone(result); await changed('Private document imported into this session.'); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <Dialog title="Bring your own context." eyebrow="PRIVATE DOCUMENTS" onClose={onClose}><p className="dialog-intro">Inspect a contract, clause, or note alongside the sources. Your upload stays in this browser session’s local collection.</p><form onSubmit={upload}><label className={`upload-zone ${drag ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); choose(e.dataTransfer.files[0]); }}><input type="file" accept=".pdf,.txt,.md" onChange={e => choose(e.target.files[0])} disabled={busy} /><span className="upload-icon"><Upload size={27} strokeWidth={1.4} /></span><strong>{file ? file.name : 'Drop a document here'}</strong><span>{file ? `${(file.size / 1024).toFixed(1)} KiB · click to change` : 'or click to browse your files'}</span><small>PDF, TXT, Markdown · up to 25 MiB</small></label><Select label="Document domain" value={domain} onChange={e => setDomain(e.target.value)}>{domainInfo.map(d => <option key={d.name} value={d.name}>{d.short}</option>)}</Select><Notice>Uploads are private facts, not legal authorities. Scanned PDFs may require OCR, which this project does not perform. Files persist locally until explicitly cleared.</Notice>{error && <Notice error>{error}</Notice>}{done && <div className="upload-success" role="status"><CheckCircle2 size={20} /><div><strong>{done.created ? 'Document imported' : 'Existing duplicate retained'}</strong><p>{done.chunks} searchable passages.{done.warnings.map(w => ` ${w}`).join('')}</p></div></div>}<Button type="submit" className="primary upload-submit" icon={busy ? LoaderCircle : Upload} disabled={!file || busy}>{busy ? 'Importing document…' : 'Import private document'}</Button></form></Dialog>;
}

function Stat({ label, value, icon: Icon, sub }) { return <div className="stat-card"><div><span>{label}</span><strong>{value}</strong>{sub && <small>{sub}</small>}</div><span className="stat-icon"><Icon size={18} strokeWidth={1.5} /></span></div>; }
function Coverage({ boot, onDomain }) {
  return <><PageHeading eyebrow="KNOW THE BOUNDARIES" title="Coverage, made visible." description="A clear view of what is collected, indexed, and reviewed in your local corpus." /><div className="stats-row"><Stat label="Distinct sources" value={boot.totals.sources} icon={Library} /><Stat label="Source versions" value={boot.totals.versions} icon={FileText} /><Stat label="Active indexed" value={boot.totals.indexed} icon={BookOpen} /><Stat label="Reviewed versions" value={boot.totals.reviewed} icon={ShieldCheck} /></div><Notice>Representative coverage does not establish completeness or current law. State/UT collections, case law, and several personal laws are not included. Unknown effective dates remain unknown. Shared sources count once within each domain and once in the total collection.</Notice><div className="coverage-grid">{domainInfo.map((d, i) => { const row = boot.coverage.find(r => r.domain === d.name); return <article className="coverage-card" key={d.name} style={{ '--delay': `${i * 35}ms` }}><div className="coverage-card-head"><span className={`domain-icon color-${i % 4}`}><d.icon size={21} strokeWidth={1.5} /></span><h3>{d.short}</h3></div><p className="muted">{row.primary_sources} primary sources{row.related_sources > 0 && ` · ${row.related_sources} sources with selected related passages`}</p><div className="coverage-values">{[['Collected', row.collected], ['Parsed', row.parsed], ['Indexed', row.indexed], ['Reviewed', row.reviewed]].map(([k, v]) => <div key={k}><span>{k}</span><strong>{v}</strong></div>)}</div><div className="coverage-bar" aria-label={`${row.reviewed} reviewed out of ${row.versions} versions`}><span className="indexed-bar" style={{ width: `${row.versions ? row.indexed / row.versions * 100 : 0}%` }} /><span className="reviewed-bar" style={{ width: `${row.versions ? row.reviewed / row.versions * 100 : 0}%` }} /></div><div className="coverage-bottom"><span>{row.states.length ? row.states.join(', ') : 'State / UT coverage not established'}</span><button className="text-link" onClick={() => onDomain(d)} aria-label={`Research ${d.short}`}><ArrowUpRight size={16} /></button></div></article>; })}</div><div className="coverage-legend"><span><i className="indexed-key" /> Indexed versions</span><span><i className="reviewed-key" /> Reviewed versions</span></div></>;
}

function Evaluation() {
  const [data, setData] = useState(null), [error, setError] = useState('');
  useEffect(() => { api('/evaluation').then(setData).catch(e => setError(e.message)); }, []);
  const report = data?.report, summary = report?.summaries?.bm25;
  return <><PageHeading eyebrow="MEASURED, NOT ASSUMED" title="Research under review." description="Recorded retrieval results, with their corpus snapshot and limits attached." />{error && <Notice error>{error}</Notice>}{!data ? <div className="inline-loading"><LoaderCircle className="spin" size={18} /> Reading the benchmark report…</div> : !report ? <Empty icon={FlaskConical} title="No measured report yet">Run the evaluation CLI after importing the benchmark corpus.</Empty> : <>{!data.matches_corpus && <Notice error>This saved report belongs to a different corpus snapshot. Rerun the benchmark before treating these measurements as results for this workspace.</Notice>}<div className="evaluation-banner"><span className="evaluation-icon"><FlaskConical size={28} strokeWidth={1.4} /></span><div><h3>{report.split === 'heldout' ? 'Held-out' : report.split} retrieval benchmark</h3><p>{report.case_count} cases · recorded {new Date(report.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</p></div><Badge tone={data.matches_corpus ? 'green' : 'amber'}>{data.matches_corpus ? 'Matches local corpus' : 'Different snapshot'}</Badge></div><div className="stats-row"><Stat label={`BM25 Recall@${report.k}`} value={summary?.recall_at_k == null ? 'Not measured' : `${(summary.recall_at_k * 100).toFixed(1)}%`} icon={Search} sub={`${summary?.evidence_scored_cases || 0} evidence-scored cases`} /><Stat label="Mean reciprocal rank" value={summary?.mrr?.toFixed(3) || 'Not measured'} icon={ChartNoAxesCombined} /><Stat label="Median search latency" value={summary?.median_latency_seconds == null ? 'Not measured' : `${summary.median_latency_seconds.toFixed(2)}s`} icon={Cpu} sub="Recorded cloud environment" /><Stat label="Human legal review" value="Pending" icon={Shield} sub="Semantic support not certified" /></div><Notice>These author-defined passage labels measure retrieval and engineering behavior. Human semantic/legal review and laptop performance measurements are pending. Dense and hybrid runs require actual local model weights and indexes.</Notice><div className="evaluation-table-wrap"><table className="evaluation-table"><thead><tr><th>CASE</th><th>METHOD</th><th>OUTCOME</th><th>RECALL</th><th>LEGAL SUPPORT</th></tr></thead><tbody>{report.rows.map((r, i) => <tr key={i}><td>{r.case_id}</td><td>{r.mode}</td><td><Badge tone={r.status === 'run' ? 'green' : ''}>{r.status}</Badge></td><td>{r.recall_at_k == null ? '—' : `${(r.recall_at_k * 100).toFixed(0)}%`}</td><td>{r.human_legal_support || 'Not assessed'}</td></tr>)}</tbody></table></div><details className="details-panel"><summary>Report environment & source snapshot <ChevronDown size={15} /></summary><pre>{JSON.stringify({ corpus_signature: report.corpus_signature, environment: report.environment, summaries: report.summaries }, null, 2)}</pre></details></>}</>;
}

function WorkspaceSettings({ boot, profile, setProfile, changed }) {
  const [diagnostics, setDiagnostics] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(''), [confirmClear, setConfirmClear] = useState(false), [result, setResult] = useState(null);
  useEffect(() => { let live = true; setDiagnostics(null); api(`/diagnostics?profile=${profile}`).then(d => live && setDiagnostics(d)).catch(e => live && setError(e.message)); return () => { live = false; }; }, [profile, boot.revision]);
  async function action(key) {
    setBusy(key); setError(''); setResult(null);
    try { const data = await post(key === 'clear' ? '/private/clear' : `/corpus/${key}`); setResult({ key, data }); await changed(key === 'clear' ? 'This session’s private files and answers cleared.' : 'Source collection updated.'); setConfirmClear(false); }
    catch (e) { setError(e.message); } finally { setBusy(''); }
  }
  return <><PageHeading eyebrow="MAKE IT YOUR WORKSPACE" title="A local-first setup." description="Choose your research profile, manage collections, and check what is ready." />{error && <Notice error>{error}</Notice>}<div className="settings-grid"><section className="settings-card"><div className="settings-card-title"><Cpu size={20} /><h2>Research engine</h2></div><Select label="Hardware & model profile" value={profile} onChange={e => setProfile(e.target.value)}><option value="evidence_only">Evidence only · no model required</option><option value="lenovo_cpu">Lenovo / CPU · local Ollama candidate</option><option value="mac_m5">Mac / M5 · local Ollama candidate</option></Select><p>BM25 and exact source extracts work offline. Model profiles use your separately installed Ollama and cached weights.</p><div className="engine-status"><span className="status-dot" /><strong>BM25 retrieval ready</strong></div><div className="engine-status"><span className={`status-dot ${diagnostics?.ollama.model_available ? '' : 'muted-dot'}`} /><strong>{!diagnostics ? 'Checking local model…' : diagnostics.ollama.model_available ? 'Selected Ollama model available' : 'Local generation unavailable'}</strong></div>{diagnostics && <p className="muted">{diagnostics.ollama.message}</p>}<details className="details-panel"><summary>Technical diagnostics <ChevronDown size={14} /></summary>{diagnostics ? <pre>{JSON.stringify(diagnostics, null, 2)}</pre> : <span>Checking…</span>}</details></section>
      <section className="settings-card"><div className="settings-card-title"><Library size={20} /><h2>Source collections</h2></div><p>The project includes {boot.bundle_sources} source documents and eight search indexes across all eight domains. Loading retains unreviewed status, manual changes, and source notices.</p><div className="collection-actions">{boot.bundle_available && <Button disabled={!!busy} icon={busy === 'bundled' ? LoaderCircle : Download} onClick={() => action('bundled')}>Load project documents offline</Button>}<Button disabled={!!busy} icon={busy === 'acquire' ? LoaderCircle : Globe} onClick={() => action('acquire')}>Acquire official sample online</Button><Button disabled={!!busy} icon={busy === 'synthetic' ? LoaderCircle : FlaskConical} onClick={() => action('synthetic')}>Load synthetic classroom fixture</Button></div><span className="settings-note">Online acquisition checks allowed HTTPS hosts, titles, and file hashes. Synthetic fixtures remain separate from official sources.</span>{result && result.key !== 'clear' && <details className="details-panel" open><summary>Collection result <ChevronDown size={14} /></summary><pre>{JSON.stringify(result.data, null, 2)}</pre></details>}</section>
      <section className="settings-card private-settings"><div className="settings-card-title"><LockKeyhole size={20} /><h2>Your private session</h2><Badge>{boot.private_sources} files</Badge></div><p>Private questions are not logged by default. Uploads persist in local storage until you clear them. Clearing deletes this session’s uploaded originals and research cache; files are not encrypted or securely erased.</p>{confirmClear ? <div className="clear-confirm"><strong>Delete this session’s private uploads and answers?</strong><div className="reader-actions"><Button className="danger" icon={Trash2} disabled={!!busy} onClick={() => action('clear')}>Delete private files</Button><Button onClick={() => setConfirmClear(false)}>Keep files</Button></div></div> : <Button icon={Trash2} onClick={() => setConfirmClear(true)} disabled={!!busy}>Clear this session’s private files</Button>}</section></div></>;
}

class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="boot-error"><h1>Something interrupted the workspace.</h1><p>Reload to reconnect to the local research engine.</p><Button onClick={() => location.reload()}>Reload workspace</Button></div> : this.props.children; }
}
createRoot(document.getElementById('root')).render(<ErrorBoundary><App /></ErrorBoundary>);
