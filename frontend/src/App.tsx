import { useCallback, useEffect, useState, type ReactNode } from 'react'

const API = 'http://127.0.0.1:8010/api'
type Page = 'Overview' | 'Assets' | 'Exposure changes' | 'Investigations' | 'Snapshots' | 'Demo control'
type AnyRow = Record<string, any>

const navigation: { name: Page; icon: string }[] = [
  { name: 'Overview', icon: '◫' }, { name: 'Assets', icon: '▦' },
  { name: 'Exposure changes', icon: '↗' }, { name: 'Investigations', icon: '◎' },
  { name: 'Snapshots', icon: '◷' }, { name: 'Demo control', icon: '▷' },
]

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`)
  return data
}

function time(value?: string) {
  if (!value) return 'No observation yet'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function App() {
  const [page, setPage] = useState<Page>('Overview')
  const [summary, setSummary] = useState<AnyRow>({})
  const [assets, setAssets] = useState<AnyRow[]>([])
  const [services, setServices] = useState<AnyRow[]>([])
  const [cases, setCases] = useState<AnyRow[]>([])
  const [observations, setObservations] = useState<AnyRow[]>([])
  const [snapshots, setSnapshots] = useState<AnyRow[]>([])
  const [changes, setChanges] = useState<AnyRow[]>([])
  const [selectedCase, setSelectedCase] = useState<number | null>(null)
  const [caseDetail, setCaseDetail] = useState<AnyRow | null>(null)
  const [note, setNote] = useState('')
  const [toast, setToast] = useState('')
  const [busy, setBusy] = useState(false)
  const [online, setOnline] = useState(false)
  const refresh = useCallback(async () => {
    try {
      const [s, a, svc, c, o, sn, ch] = await Promise.all([
        request('/dashboard/summary'), request('/assets'), request('/services'), request('/incidents'),
        request('/observations'), request('/snapshots'), request('/changes'),
      ])
      setSummary(s); setAssets(a); setServices(svc); setCases(c); setObservations(o); setSnapshots(sn); setChanges(ch); setOnline(true)
    } catch { setOnline(false) }
  }, [])
  useEffect(() => { void refresh(); const id = window.setInterval(refresh, 6000); return () => clearInterval(id) }, [refresh])
  useEffect(() => { if (selectedCase) request(`/incidents/${selectedCase}`).then(setCaseDetail).catch(() => setCaseDetail(null)) }, [selectedCase, cases])
  useEffect(() => { if (toast) { const id = window.setTimeout(() => setToast(''), 3600); return () => clearTimeout(id) } }, [toast])

  async function action(path: string, method = 'POST', body?: AnyRow, success?: string) {
    setBusy(true)
    try { const result = await request(path, { method, body: body ? JSON.stringify(body) : undefined }); if (success) setToast(success); await refresh(); return result }
    catch (e) { setToast(e instanceof Error ? e.message : 'Action failed'); return null }
    finally { setBusy(false) }
  }
  const activeCases = cases.filter(c => !['resolved', 'approved_change'].includes(c.status))
  const pageIntro: Record<Page, string> = {
    'Overview': 'Change-focused visibility for approved infrastructure.',
    'Assets': 'Fictional inventory and the services expected on each asset.',
    'Exposure changes': 'Observed service changes with their source and evidence.',
    'Investigations': 'Evidence-backed reviews with an auditable case history.',
    'Snapshots': 'Synthetic DNS and certificate metadata comparisons.',
    'Demo control': 'Run the presenter scenarios and restore the local lab.',
  }
  const latestObservation = observations[0]
  const management = services.find(s => s.kind === 'management')

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">P</div><div><strong>OQVIAN</strong><span>PERIVANT</span></div></div>
      <div className="workspace"><small>WORKSPACE</small><div className="workspace-name"><i /> AsterGate Cloud Services <span>⌄</span></div></div>
      <div className="nav-label">COMMAND</div>
      <nav>{navigation.map(item => <button key={item.name} title={item.name} aria-label={item.name} className={page === item.name ? 'nav-item active' : 'nav-item'} onClick={() => setPage(item.name)}><span className="nav-icon">{item.icon}</span>{item.name}{item.name === 'Investigations' && activeCases.length > 0 && <b>{activeCases.length}</b>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-card"><span className="local-dot"/><div><strong>Local demo environment</strong><small>No external scans enabled</small></div></div><div className="sidebar-foot">OQVIAN SECURITY SYSTEMS <span>v0.1 DEMO</span></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumbs"><span>PERIVANT</span><b>/</b>{page.toUpperCase()}</div><div className="top-actions"><div className="system-state"><span className={online ? 'status-led' : 'status-led off'} />{online ? 'SYSTEM ONLINE' : 'API DISCONNECTED'}</div><button className="icon-btn" title="Refresh" onClick={() => void refresh()}>↻</button><div className="avatar">DA</div></div></header>
      <div className="content">
        <div className="page-head"><div><div className="eyebrow"><span className="eyebrow-line"/> EXPOSURE INTELLIGENCE <span className="env-tag">LOCAL DEMO</span></div><h1>{page}</h1><p>{pageIntro[page]}</p></div><div className="head-actions"><span className="sync-copy">LAST OBSERVED<br/><strong>{time(summary.last_observation)}</strong></span><button className="button button-primary" disabled={busy || !online} onClick={() => action('/observations/run', 'POST', undefined, 'Local observation completed.')}>◉ <span>Run observation</span></button></div></div>

        {page === 'Overview' && <>
          <div className="notice"><span className="notice-icon">i</span><div><strong>Scope is deliberately limited</strong><span>Service observations are from application-owned 127.0.0.1 lab listeners. DNS and TLS cards use synthetic snapshots. This demo does not scan the public internet.</span></div><span className="notice-label">PROVENANCE ACTIVE</span></div>
          <div className="metric-grid">
            <Metric label="INVENTORIED ASSETS" value={summary.asset_count ?? '—'} sub="Fictional demo inventory" icon="▦" />
            <Metric label="OPEN INVESTIGATIONS" value={summary.open_cases ?? '—'} sub={activeCases.length ? `${activeCases.length} require review` : 'No active cases'} icon="◎" accent={activeCases.length > 0} />
            <Metric label="HIGH PRIORITY" value={summary.high_priority ?? '—'} sub="Policy based · no probability score" icon="↗" accent={!!summary.high_priority} />
            <Metric label="REGISTERED SERVICES" value={summary.observed_services ?? '—'} sub="App-owned lab registry" icon="⊞" />
          </div>
          <div className="overview-grid">
            <section className="panel asset-panel"><PanelHead title="Asset exposure" sub="Approved scope · fictional inventory" right={<button className="text-button" onClick={() => setPage('Assets')}>All assets <span>→</span></button>} />
              <div className="table-wrap"><table><thead><tr><th>ASSET</th><th>CLASSIFICATION</th><th>OWNER</th><th>SERVICES</th><th>STATE</th></tr></thead><tbody>{assets.map(a => { const own = services.filter(s => s.asset_id === a.id); return <tr key={a.id} onClick={() => setPage('Assets')}><td><strong>{a.name}</strong><small>{a.category}</small></td><td><span className={`criticality ${a.criticality}`}>{a.criticality}</span></td><td>{a.owner}</td><td>{own.length.toString().padStart(2, '0')}</td><td><span className="state-good"><i/> {own.some(s => s.running) ? 'OBSERVING' : 'IDLE'}</span></td></tr>})}</tbody></table></div>
            </section>
            <section className="panel cases-panel"><PanelHead title="Investigation queue" sub="Prioritized for analyst review" right={<button className="text-button" onClick={() => setPage('Investigations')}>View all <span>→</span></button>} />
              {activeCases.length === 0 ? <Empty icon="✓" title="No active investigations" copy="Run a demo scenario to introduce an evidence-backed change."/> : <div className="case-list">{activeCases.slice(0, 4).map(c => <CaseRow key={c.id} item={c} onClick={() => { setSelectedCase(c.id); setPage('Investigations') }} />)}</div>}
            </section>
            <section className="panel activity-panel"><PanelHead title="Observation stream" sub="Most recent registered checks" right={<span className="live-tag"><i/>LOCAL</span>} />
              {observations.length === 0 ? <Empty icon="◷" title="No observations recorded" copy="Start an observation to capture the approved baseline."/> : <div className="activity-list">{observations.slice(0, 5).map(o => <div className="activity-row" key={o.id}><span className={o.state === 'reachable' ? 'activity-symbol green' : o.state === 'unavailable' ? 'activity-symbol muted' : 'activity-symbol amber'}>{o.state === 'reachable' ? '✓' : o.state === 'unavailable' ? '−' : '?'}</span><div><strong>{o.state === 'reachable' ? 'Service reachable' : o.state === 'unavailable' ? 'Service unavailable' : 'Observation inconclusive'}</strong><small>127.0.0.1:{o.port} · run #{o.run_id}</small></div><time>{time(o.created_at)}</time></div>)}</div>}
            </section>
            <section className="panel scenarios-panel"><PanelHead title="Demo scenarios" sub="Controlled, repeatable demonstrations" right={<button className="text-button" onClick={() => setPage('Demo control')}>Open control <span>→</span></button>} />
              <div className="scenario-shortcuts"><button onClick={() => action('/demo/scenarios/management-exposure/run', 'POST', undefined, 'Management service scenario started.')}><span className="scenario-num">01</span><span><strong>Unexpected management service</strong><small>Local lab · R001 / R002 / R007</small></span><b>↗</b></button><button onClick={() => action('/demo/scenarios/dns-drift/run', 'POST', undefined, 'Synthetic DNS drift compared.')}><span className="scenario-num">02</span><span><strong>DNS configuration drift</strong><small>Synthetic snapshot · R004 / R006</small></span><b>↗</b></button></div>
            </section>
          </div>
        </>}

        {page === 'Assets' && <section className="panel full-panel"><PanelHead title="Asset inventory" sub="ASTERGATE CLOUD SERVICES · all assets are fictional" right={<span className="count-tag">{assets.length} ASSETS</span>} /><div className="table-wrap"><table><thead><tr><th>ASSET</th><th>TYPE</th><th>CRITICALITY</th><th>OWNER</th><th>APPROVED SERVICES</th><th>OBSERVED</th></tr></thead><tbody>{assets.map(a => { const own=services.filter(s=>s.asset_id===a.id); return <tr key={a.id}><td><strong>{a.name}</strong><small>DEMO ASSET · LOCAL INVENTORY</small></td><td>{a.category}</td><td><span className={`criticality ${a.criticality}`}>{a.criticality}</span></td><td>{a.owner}</td><td>{own.filter(s=>s.approved).length} approved · {own.filter(s=>!s.approved).length} unapproved</td><td><span className={own.some(s=>s.running)?'state-good':'state-idle'}><i/>{own.some(s=>s.running)?'ACTIVE':'IDLE'}</span></td></tr>})}</tbody></table></div></section>}

        {page === 'Exposure changes' && <div className="stack"><section className="panel full-panel"><PanelHead title="Registered services" sub="Only entries in the local lab registry can be observed" right={<span className="live-tag"><i/>127.0.0.1 ONLY</span>} /><div className="table-wrap"><table><thead><tr><th>SERVICE</th><th>ASSET</th><th>LOCAL ENDPOINT</th><th>POLICY</th><th>LIVE STATE</th><th>TYPE</th></tr></thead><tbody>{services.map(s => <tr key={s.id}><td><strong>{s.name}</strong></td><td>{assets.find(a=>a.id===s.asset_id)?.name}</td><td className="mono">{s.host}:{s.port}</td><td><span className={s.approved?'approval approved':'approval unapproved'}>{s.approved?'APPROVED':'UNAPPROVED'}</span></td><td><span className={s.running?'state-good':'state-idle'}><i/>{s.running?'REACHABLE':'UNAVAILABLE'}</span></td><td><span className="type-tag">{s.kind}</span></td></tr>)}</tbody></table></div></section><section className="panel full-panel"><PanelHead title="Recent observations" sub="Saved evidence from local loopback checks" /><div className="table-wrap"><table><thead><tr><th>RUN</th><th>ENDPOINT</th><th>RESULT</th><th>SOURCE</th><th>EVIDENCE</th></tr></thead><tbody>{observations.slice(0,20).map(o=><tr key={o.id}><td>#{o.run_id}</td><td className="mono">{o.host}:{o.port}</td><td><span className={o.state==='reachable'?'state-good':o.state==='unavailable'?'state-idle':'state-unknown'}><i/>{o.state.toUpperCase()}</span></td><td><span className="source-tag local">LOCAL LAB</span></td><td className="evidence-cell">{o.evidence}</td></tr>)}</tbody></table></div></section></div>}

        {page === 'Investigations' && <div className="investigation-layout"><section className="panel full-panel"><PanelHead title="Investigation cases" sub="Persistent findings · deterministic rules · no attack probability score" right={<span className="count-tag">{cases.length} TOTAL</span>} />{cases.length===0?<Empty icon="◎" title="No investigation cases" copy="Run the management, DNS, or TLS scenario to create an evidence-backed review."/>:<div className="case-list roomy">{cases.map(c=><CaseRow key={c.id} item={c} selected={selectedCase===c.id} onClick={()=>setSelectedCase(c.id)}/>)}</div>}</section>
          <section className="panel detail-panel">{!caseDetail?<Empty icon="⌁" title="Select a case" copy="Choose an investigation to inspect its evidence and timeline."/>:<><PanelHead title="Case detail" sub={`CASE · PV-${String(caseDetail.id).padStart(4,'0')}`} right={<span className={`criticality ${caseDetail.priority}`}>{caseDetail.priority}</span>}/><div className="case-detail-body"><div className="detail-title"><h2>{caseDetail.title}</h2><span className="source-tag">{caseDetail.source_mode==='local_lab_observation'?'LOCAL LAB OBSERVATION':'SYNTHETIC SNAPSHOT'}</span></div><p className="detail-copy">{caseDetail.explanation}</p><div className="detail-facts"><Fact label="ASSET" value={caseDetail.asset}/><Fact label="OWNER" value={caseDetail.owner}/><Fact label="PREVIOUS" value={caseDetail.previous_state}/><Fact label="CURRENT" value={caseDetail.current_state}/><Fact label="ENDPOINT" value={caseDetail.port ? `${caseDetail.host}:${caseDetail.port}` : caseDetail.host}/><Fact label="APPROVAL" value={caseDetail.approved?'Approved':'No matching approval'}/></div><div className="rule-line"><span>TRIGGERED RULES</span>{caseDetail.rule_ids?.map((r:string)=><b key={r}>{r}</b>)}</div><div className="evidence-box"><div className="evidence-head"><strong>Evidence record</strong><span>● VERIFIED SOURCE</span></div><pre>{caseDetail.evidence}</pre></div><div className="case-actions"><label>CASE STATUS<select value={caseDetail.status} onChange={e=>void action(`/incidents/${caseDetail.id}`,'PATCH',{status:e.target.value},'Case status updated.')}><option value="new">New</option><option value="acknowledged">Acknowledged</option><option value="investigating">Investigating</option><option value="approved_change">Approved change</option><option value="remediation_planned">Remediation planned</option><option value="resolved" disabled={caseDetail.source_mode==='local_lab_observation'&&caseDetail.status!=='resolved'}>Resolved after verification</option><option value="reopened">Reopened</option></select></label><label>ASSIGNEE<select value={caseDetail.owner} onChange={e=>void action(`/incidents/${caseDetail.id}`,'PATCH',{owner:e.target.value},'Case owner updated.')}><option>{caseDetail.owner}</option><option>Security Operations</option><option>Infrastructure Security</option><option>Platform Operations</option></select></label></div><form className="note-form" onSubmit={e=>{e.preventDefault(); if(note.trim()){void action(`/incidents/${caseDetail.id}/notes`,'POST',{content:note,author:'Demo Analyst'},'Investigation note saved.');setNote('')}}}><label>INVESTIGATION NOTE</label><textarea value={note} onChange={e=>setNote(e.target.value)} placeholder="Add a short analyst note..." maxLength={2000}/><button className="button button-subtle" disabled={busy||!note.trim()}>Add note <span>→</span></button></form>{caseDetail.notes?.length>0&&<div className="notes-list"><span className="eyebrow-small">CASE NOTES</span>{caseDetail.notes.map((n:AnyRow)=><div key={n.id}><strong>{n.author}</strong><time>{time(n.created_at)}</time><p>{n.content}</p></div>)}</div>}{caseDetail.timeline?.length>0&&<div className="timeline"><span className="eyebrow-small">AUDIT TIMELINE</span>{caseDetail.timeline.map((e:AnyRow)=><div key={e.id}><i/><strong>{e.action.replaceAll('_',' ')}</strong><small>{time(e.created_at)}</small></div>)}</div>}{management&&caseDetail.port===management.port&&caseDetail.status!=='resolved'&&<button className="button button-primary wide" disabled={busy} onClick={()=>action('/demo/remediate','POST',undefined,'Listener stopped and verified by a fresh observation.')}>✓ &nbsp; Simulate remediation and verify</button>}</div></>}</section></div>}

        {page === 'Snapshots' && <div className="snapshot-grid">{(['dns','tls'] as const).map(kind=>{const rows=snapshots.filter(s=>s.type===kind); const latest=rows[0]; return <section className="panel snapshot-card" key={kind}><PanelHead title={kind==='dns'?'DNS record snapshots':'TLS certificate metadata'} sub={kind==='dns'?'A · AAAA · CNAME · MX · NS · TXT':'Fingerprint · Subject · Issuer · Validity · SAN'} right={<span className="source-tag synthetic">SYNTHETIC</span>}/><div className="snapshot-domain">{latest?.key||'portal.astergate.example'}</div><div className="snapshot-table">{latest&&Object.entries(latest.values).map(([k,v])=><div key={k}><span>{k.toUpperCase()}</span><code>{Array.isArray(v)?v.join(', '):String(v)}</code></div>)}</div><div className="snapshot-foot"><span>Snapshot set · {rows.length}</span><button className="button button-subtle" disabled={busy} onClick={()=>action(`/demo/scenarios/${kind==='dns'?'dns-drift':'tls-change'}/run`,'POST',undefined,`${kind.toUpperCase()} synthetic comparison completed.`)}>Run change scenario →</button></div></section>})}<section className="panel snapshot-info"><div className="info-symbol">i</div><div><strong>Source labeling matters</strong><p>These records are fictional, synthetic fixtures under <code>.example</code>. PERIVANT does not query public DNS or establish TLS connections in this demo.</p></div></section><section className="panel snapshot-card"><PanelHead title="Change register" sub="Fictional approval context" right={<span className="count-tag">{changes.length} RECORDS</span>}/>{changes.map(c=><div className="change-row" key={c.id}><span className={c.approval_status==='approved'?'change-check':'change-pending'}>{c.approval_status==='approved'?'✓':'!'}</span><div><strong>{c.title}</strong><small>{c.approved_by||'No approver recorded'} · {c.scenario_id}</small><p>{c.details}</p></div></div>)}</section></div>}

        {page === 'Demo control' && <div className="demo-layout"><section className="panel demo-main"><PanelHead title="Presenter scenarios" sub="Each action runs against controlled local or synthetic fixtures" right={<span className="type-tag">ACTIVE · {String(summary.active_scenario||'baseline').replaceAll('-',' ').toUpperCase()}</span>}/><div className="scenario-cards">
            <Scenario id="01" title="Unexpected management service" text="Start a harmless localhost listener, compare it with the approved baseline, and open a policy review case." tags={['LOCAL LAB','R001 · R002 · R007']} onRun={()=>action('/demo/scenarios/management-exposure/run','POST',undefined,'Management service detected in local lab observation.')}/>
            <Scenario id="02" title="DNS configuration drift" text="Compare synthetic DNS record sets and show exact before/after values with approval context." tags={['SYNTHETIC','R004 · R006']} onRun={()=>action('/demo/scenarios/dns-drift/run','POST',undefined,'Synthetic DNS comparison completed.')}/>
            <Scenario id="03" title="TLS metadata change" text="Compare certificate metadata fixtures. No TLS connection or trust-store change is performed." tags={['SYNTHETIC','R005 · R006']} onRun={()=>action('/demo/scenarios/tls-change/run','POST',undefined,'Synthetic TLS comparison completed.')}/>
            <Scenario id="04" title="Approved maintenance" text="Introduce a registered lab service with an explicit fictional approval. Preserve the evidence without an urgent incident." tags={['LOCAL LAB','APPROVED CHANGE']} onRun={()=>action('/demo/scenarios/approved-maintenance/run','POST',undefined,'Approved maintenance scenario recorded.')}/>
          </div><div className="demo-toolbar"><button className="button button-subtle" disabled={busy} onClick={()=>action('/observations/run','POST',undefined,'Observation completed.')}>◉ Run local observation</button><button className="button button-subtle" disabled={busy} onClick={()=>action('/lab/start','POST',undefined,'Baseline lab listeners started.')}>Start baseline lab</button><button className="button button-subtle" disabled={busy} onClick={()=>action('/lab/stop','POST',undefined,'Only local lab listeners were stopped.')}>Stop lab listeners</button></div></section><aside className="panel reset-panel"><div className="reset-icon">↺</div><span className="eyebrow-small">PRESENTER TOOLS</span><h2>Restore starting state</h2><p>Stops only listeners owned by PERIVANT and rebuilds the fictional demo fixtures. No unrelated process is touched.</p><button className="button button-danger" disabled={busy} onClick={()=>action('/demo/reset','POST',undefined,'Demo reset to its starting state.')}>Reset demo</button><div className="reset-note">Reset clears this demo’s SQLite records and restores the approved baseline.</div></aside></div>}
        <footer className="page-footer"><span>OQVIAN PERIVANT <b>·</b> EXPOSURE CHANGE INTELLIGENCE</span><span>DEMO DATA ONLY <i/> LOCAL EXECUTION</span></footer>
      </div>
    </main>
    {toast&&<div className="toast"><span>✓</span>{toast}</div>}
    {busy&&<div className="busy-bar"/>}
  </div>
}

function Metric({label,value,sub,icon,accent=false}:{label:string,value:any,sub:string,icon:string,accent?:boolean}){return <div className="metric-card"><div className="metric-top"><span>{label}</span><b>{icon}</b></div><strong className={accent?'metric-accent':''}>{value}</strong><small>{sub}</small><div className="metric-bottom"><i className={accent?'red':'neutral'}/><span>{accent?'REQUIRES ATTENTION':'CURRENT STATE'}</span></div></div>}
function PanelHead({title,sub,right}:{title:string,sub?:string,right?:ReactNode}){return <div className="panel-head"><div><h2>{title}</h2>{sub&&<p>{sub}</p>}</div>{right}</div>}
function CaseRow({item,selected,onClick}:{item:AnyRow,selected?:boolean,onClick:()=>void}){return <button className={`case-row ${selected?'selected':''}`} onClick={onClick}><span className={`case-priority ${item.priority}`}>{item.priority==='high'?'!':'↗'}</span><span className="case-info"><strong>{item.title}</strong><small>{item.asset} · {item.rule_ids?.join(' / ')}</small></span><span className={`case-status ${item.status}`}>{String(item.status).replaceAll('_',' ')}</span><span className="case-arrow">→</span></button>}
function Fact({label,value}:{label:string,value:any}){return <div className="fact"><span>{label}</span><strong>{value||'—'}</strong></div>}
function Empty({icon,title,copy}:{icon:string,title:string,copy:string}){return <div className="empty"><span>{icon}</span><strong>{title}</strong><p>{copy}</p></div>}
function Scenario({id,title,text,tags,onRun}:{id:string,title:string,text:string,tags:string[],onRun:()=>void}){return <article className="scenario-card"><div className="scenario-head"><span>{id}</span><button onClick={onRun}>Run scenario <b>→</b></button></div><h3>{title}</h3><p>{text}</p><div className="scenario-tags">{tags.map(t=><span key={t}>{t}</span>)}</div></article>}

export default App
