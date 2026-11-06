import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, Radar, Wallet, ArrowUpRight, ArrowDownRight, ArrowRight, Check,
  CircleHelp, Clock3, Compass, Database, ExternalLink, Layers3, LayoutDashboard,
  ListFilter, RefreshCw, Search, ShieldCheck, SlidersHorizontal, Target,
  TrendingUp, X, Zap, AlertTriangle, CircleDot, Menu, LockKeyhole, LogOut } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts';
import './style.css';
import './brand.css';

const money = (n, digits = 2) => n == null ? '—' : new Intl.NumberFormat('en-US', {style:'currency', currency:'USD', minimumFractionDigits:digits, maximumFractionDigits:digits}).format(n);
const number = (n, digits = 2) => n == null ? '—' : new Intl.NumberFormat('es-EC', { maximumFractionDigits:digits }).format(n);
const pct = n => n == null ? '—' : `${n > 0 ? '+' : ''}${number(n)}%`;
const price = n => money(n, n < 1 ? 6 : n < 100 ? 4 : 2);
const time = n => n ? new Date(n).toLocaleTimeString('es-EC', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';
const date = n => n ? new Date(n).toLocaleString('es-EC', {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '—';
const volume = n => n >= 1e9 ? `$${number(n/1e9,1)}B` : `$${number(n/1e6,1)}M`;
const names = { WATCH:'OBSERVANDO', ENTERED:'ENTRADA PAPER', REJECTED:'DESCARTADA', ALREADY_EVALUATED:'REGISTRADA' };
const nav = [ ['overview', LayoutDashboard, 'Vista general'], ['scanner', Radar, 'Escáner de mercado'], ['portfolio', Wallet, 'Cartera paper'], ['decisions', Layers3, 'Decisiones'], ['strategy', SlidersHorizontal, 'Estrategia'] ];

async function fetchJson(path, signal) {
  const response = await fetch(path, { signal, cache:'no-store' });
  if (!response.ok) throw new Error(`Servicio no disponible (${response.status})`);
  return response.json();
}

function Login({onLogin}) {
  const [username,setUsername]=useState('elkinpabon');
  const [pin,setPin]=useState('');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const submit=async e=>{e.preventDefault();setBusy(true);setError('');try{await onLogin(username,pin);}
    catch(err){setError(err.message);}finally{setBusy(false);}};
  return <main className="login-shell"><section className="login-card">
    <div className="login-brand"><img className="bull-logo login-bull" src="/trademerc.png" alt="Toro TRADEMERC"/><div><strong>TRADEMERC</strong><small>Mercado</small></div></div>
    <div className="login-icon"><LockKeyhole size={22}/></div>
    <h1>Iniciar sesión</h1><p>Accede a tu cuenta paper de Binance Spot.</p>
    <form onSubmit={submit}>
      <label htmlFor="username">Usuario</label><input autoComplete="username" id="username" value={username} onChange={e=>setUsername(e.target.value)} required/>
      <label htmlFor="pin">PIN</label><input autoComplete="current-password" id="pin" type="password" inputMode="numeric" maxLength="64" value={pin} onChange={e=>setPin(e.target.value)} required/>
      {error&&<div className="login-error" role="alert">{error}</div>}
      <button className="login-submit" disabled={busy}>{busy?'Verificando…':'Continuar'}</button>
    </form>
    <div className="login-foot"><ShieldCheck size={15}/> Sesión privada · operaciones simuladas</div>
  </section></main>;
}

function Asset({symbol, base}) {
  const text = base || symbol.replace(/USDT$/, '');
  return <span className="asset"><span className={`coin coin-${text.length % 5}`}>{text.slice(0,2)}</span><span><strong>{text}</strong><small>{symbol}</small></span></span>;
}
function Empty({title='Aún no hay registros', children}) {
   return <div className="empty"><Radar size={30}/><h3>{title}</h3><p>{children || 'Los registros aparecerán después del próximo análisis.'}</p></div>;
}
function Tag({children, tone=''}) { return <span className={`tag ${tone}`}>{children}</span>; }
function Stat({label, value, sub, icon:Icon, tone=''}) {
  return <article className={`stat ${tone}`}><div className="stat-top"><span>{label}</span><Icon size={17}/></div><div className="stat-value">{value}</div><div className="stat-sub">{sub}</div></article>;
}
function Chart({overview}) {
  const rows = overview.curve;
  const initial = overview.account.initial;
  const values = rows.flatMap(r=>[r.equity,r.benchmark]).filter(v=>Number.isFinite(v));
  const low = Math.min(initial-.1,...values), high = Math.max(initial+.1,...values);
  return <div className="chart-body">{!rows.length ? <Empty title="Preparando curva de capital"/> : <ResponsiveContainer width="100%" height="100%"><AreaChart data={rows} margin={{top:16,right:12,left:-22,bottom:5}}>
    <defs><linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4b8f69" stopOpacity={.18}/><stop offset="100%" stopColor="#4b8f69" stopOpacity={0}/></linearGradient></defs>
    <CartesianGrid vertical={false} stroke="#dce3ed" strokeDasharray="3 6"/>
    <XAxis dataKey="at" tickFormatter={v=>new Date(v).toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit'})} tick={{fill:'#758398',fontSize:10}} axisLine={false} tickLine={false} minTickGap={55}/>
    <YAxis domain={[Math.floor(low*100)/100,Math.ceil(high*100)/100]} tickFormatter={v=>`$${v.toFixed(2)}`} tick={{fill:'#758398',fontSize:10}} axisLine={false} tickLine={false} width={68}/>
    <Tooltip contentStyle={{background:'rgba(255,255,255,.96)',border:'1px solid #dce3ed',borderRadius:16,fontSize:12,color:'#182335',boxShadow:'0 8px 30px #26385815'}} labelFormatter={date} formatter={(v,n)=>[money(v,4),n==='equity'?'TRADEMERC':'BTC buy & hold']}/>
    <ReferenceLine y={initial} stroke="#b6c3d4" strokeDasharray="4 5"/>
    <Area type="linear" dataKey="benchmark" stroke="#a99acb" strokeWidth={1.5} strokeDasharray="5 5" fill="none" connectNulls={false} isAnimationActive={false}/>
    <Area type="linear" dataKey="equity" stroke="#4b8f69" strokeWidth={2.5} fill="url(#equityFill)" isAnimationActive={false}/>
  </AreaChart></ResponsiveContainer>}</div>;
}
function App() {
  const [view,setView] = useState('overview');
  const [data,setData] = useState(null);
  const [authenticated,setAuthenticated] = useState(null);
  const [error,setError] = useState(null);
  const [refresh,setRefresh] = useState(0);
  const [search,setSearch] = useState('');
  const [filter,setFilter] = useState('all');
  const [selected,setSelected] = useState(null);
  const [mobile,setMobile] = useState(false);
  const [clock,setClock] = useState(Date.now());
  useEffect(()=>{let active=true;fetchJson('/api/auth/status').then(s=>{if(active)setAuthenticated(s.authenticated);}).catch(()=>{if(active)setAuthenticated(false);});return()=>{active=false;};},[]);
  useEffect(()=>{
    if(authenticated!==true)return;
    let busy=false, active=true;
    const controller=new AbortController();
    const load=async()=>{if(busy)return;busy=true;try{
      const [overview,opportunities,market,activity]=await Promise.all(['/api/overview','/api/opportunities','/api/market','/api/activity'].map(p=>fetchJson(p,controller.signal)));
      if(active){setData({overview,opportunities,market,activity});setError(null);}
    }catch(e){if(active && e.name!=='AbortError'){if(e.message.includes('(401)'))setAuthenticated(false);setError(e.message);}}finally{busy=false;}};
    load(); const id=setInterval(load,5000);
    return()=>{active=false;clearInterval(id);controller.abort();};
  },[refresh,authenticated]);
  useEffect(()=>{const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id);},[]);
  useEffect(()=>{const fn=e=>{if(e.key==='Escape')setSelected(null);};window.addEventListener('keydown',fn);return()=>window.removeEventListener('keydown',fn);},[]);
  const o=data?.overview, a=o?.account;
  const rows=data?.opportunities?.rows || [];
  const marketRows=useMemo(()=>{
    const decisions=new Map(rows.map(r=>[r.symbol,r]));
    return (data?.market?.rows||[]).map(q=>({...q,decision:decisions.get(q.symbol)})).filter(q=>q.symbol.toLowerCase().includes(search.toLowerCase())).filter(q=>filter==='all'||(filter==='analyzed'&&q.decision)||(filter==='ready'&&q.decision?.eligible));
  },[data,search,filter]);
  const move=v=>{setView(v);setMobile(false);};
  const online=!error && o?.health==='ONLINE' && clock-o.at<30000;
  const open=o?.positions?.[0];
  const setupCount=rows.filter(r=>r.eligible).length;
  const signIn=async(username,pin)=>{const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,pin})});const body=await res.json();if(!res.ok)throw new Error(body.detail||'No se pudo iniciar sesión');setAuthenticated(true);setRefresh(x=>x+1);};
  const signOut=async()=>{await fetch('/api/auth/logout',{method:'POST'});setAuthenticated(false);setData(null);};

  if(authenticated===null)return <div className="auth-loading"><img className="bull-logo" src="/trademerc.png" alt="Toro TRADEMERC"/><span>TRADEMERC</span></div>;
  if(authenticated===false)return <Login onLogin={signIn}/>;

  return <div className="shell">
    <aside className={`sidebar ${mobile?'is-open':''}`}>
      <a className="brand" href="#" onClick={e=>{e.preventDefault();move('overview');}}><img className="bull-logo" src="/trademerc.png" alt="Toro TRADEMERC"/><span>TRADEMERC<small>Mercado</small></span></a>
      <div className="workspace"><span className="workspace-icon"><Compass size={18}/></span><div>Cuenta personal<small>Binance Spot</small></div><Tag>Paper</Tag></div>
      <span className="nav-label">Mi espacio</span>
      <nav>{nav.map(([id,Icon,label])=><button key={id} className={`nav-item ${view===id?'active':''}`} onClick={()=>move(id)}><Icon size={18}/><span>{label}</span>{view===id&&<span className="nav-dot"/>}</button>)}</nav>
      <div className="sidebar-note"><ShieldCheck size={20}/><strong>Cuenta de simulación</strong><p>Saldo inicial de $50.<br/>Operaciones spot.</p><span>Motor intradía <b>v1.0</b></span></div>
      <div className="sidebar-bottom"><span className={`live-dot ${online?'':'warning'}`}/><span>{online?'Sistemas conectados':'Comprobando conexión'}</span><Database size={14}/></div>
    </aside>
    <div className="main">
      <header className="topbar"><div className="breadcrumbs"><button className="icon-button mobile-toggle" aria-label="Abrir menú" onClick={()=>setMobile(!mobile)}><Menu size={20}/></button><span>Cuenta</span><span className="slash">/</span><strong>{nav.find(n=>n[0]===view)[2]}</strong></div><div className="top-actions"><span className="clock"><Clock3 size={13}/>{new Date(clock).toLocaleTimeString('es-EC')}</span><Tag tone={online?'green':'amber'}><span className={`live-dot ${online?'':'warning'}`}/>{online?'En línea':o?.health==='WARMING'?'Preparando':'Verificando'}</Tag><button className="icon-button" title="Actualizar" aria-label="Actualizar datos" onClick={()=>setRefresh(x=>x+1)}><RefreshCw size={16}/></button><button className="icon-button logout" title="Cerrar sesión" aria-label="Cerrar sesión" onClick={signOut}><LogOut size={16}/></button></div></header>
      <main>
        {error&&<div role="alert" className="alert"><AlertTriangle size={17}/>{error}. {data?'Se muestran los últimos datos recibidos; pueden estar obsoletos.':'Reintentando conexión automáticamente.'}</div>}
        <div className="page-heading"><div><h1>{({overview:'Resumen',scanner:'Mercado',portfolio:'Cartera',decisions:'Actividad',strategy:'Estrategia'})[view]}</h1><p>{({overview:'Balance, mercado y operaciones.',scanner:'Pares USDT, liquidez y señales de entrada.',portfolio:'Posiciones y saldo de la cuenta paper.',decisions:'Entradas, descartes y condiciones evaluadas.',strategy:'Parámetros de momentum intradía.'})[view]}</p></div><button className="secondary-button" onClick={()=>move(view==='strategy'?'overview':'strategy')}><SlidersHorizontal size={15}/>{view==='strategy'?'Volver al resumen':'Ver estrategia'}</button></div>
        {!data ? <div className="loading-grid">{[0,1,2,3].map(n=><div className="skeleton" key={n}/>)}<div className="loading-message"><Radar className="rotate"/>Conectando con el laboratorio…</div></div> : <>
          {view==='overview'&&<>
            <section className="stats-grid">
              <Stat label="Patrimonio paper" value={money(a.equity)} sub={<><span className={a.return_pct>=0?'positive':'negative'}>{pct(a.return_pct)}</span> desde {money(a.initial)} iniciales</>} icon={Wallet} tone="featured"/>
              <Stat label="Resultado realizado" value={money(a.realized,3)} sub={`${a.trades} operaciones cerradas · fees ${money(a.fees,3)}`} icon={TrendingUp}/>
              <Stat label="Mercados descubiertos" value={number(o.universe.spot_usdt_total,0)} sub={`${number(o.scan.liquid_markets,0)} líquidos · ${o.scan.analyzed??0} analizados en profundidad`} icon={Radar}/>
              <Stat label="Setups detectados" value={String(setupCount).padStart(2,'0')} sub={`Último barrido ${time(o.scan.at)}`} icon={Target}/>
            </section>
            <div className="overview-grid"><section className="panel equity-panel"><div className="panel-head"><h2>Patrimonio</h2><div className="legend"><span><i className="mint"/>TRADEMERC</span><span><i className="purple"/>BTC</span><Tag>Desde inicio</Tag></div></div><div className="equity-summary"><strong>{money(a.equity,2)}</strong><span className={a.return_pct>=0?'positive':'negative'}>{a.return_pct>=0?<ArrowUpRight size={16}/>:<ArrowDownRight size={16}/>} {pct(a.return_pct)}</span><small>Último precio comprador</small></div><Chart overview={o}/><div className="chart-footer"><span>Referencia BTC fraccional, costes incluidos</span><span>Inicio: {date(a.started_at)}</span></div></section>
              <section className="panel engine-panel"><div className="panel-head"><h2>Escáner</h2><Radar size={19}/></div><div className="scan-orb"><Radar size={40} strokeWidth={1.3}/></div><div className="engine-title">{o.scan.analyzed??0} mercados analizados</div><div className="engine-desc">Último análisis: {time(o.scan.at)}</div><div className="engine-list"><div><span>Activos disponibles</span><strong>{o.universe.eligible_assets??'—'}</strong></div><div><span>Candidatos revisados</span><strong>{o.scan.analyzed??0} / {o.scan.attempted??0}</strong></div><div><span>Duración</span><strong>{number((o.scan.duration_ms||0)/1000,1)} s</strong></div><div><span>Errores</span><strong className={o.scan.errors?.length?'negative':''}>{o.scan.errors?.length||0}</strong></div></div></section></div>
            <div className="lower-grid"><section className="panel"><div className="panel-head"><div><h2>Oportunidades</h2><p>Ordenadas por filtros cumplidos.</p></div><button className="text-button" onClick={()=>move('scanner')}>Ver todas <ArrowRight size={15}/></button></div><OpportunityTable rows={rows.slice(0,5)} onSelect={setSelected}/></section><section className="panel exposure-panel"><div className="panel-head"><h2>Distribución</h2><Wallet size={17}/></div><div className="allocation"><div style={{width:`${Math.min(100,Math.max(0,(a.equity-a.cash)/a.equity*100))}%`}}/></div><div className="allocation-label"><span>Invertido {money(a.equity-a.cash)}</span><span>USDT {money(a.cash)}</span></div>{open?<div className="position-mini"><Asset symbol={open.symbol}/><strong>{price(open.mark)}</strong><Tag tone={open.dust?'amber':'green'}>{open.dust?'Residual':'Abierta'}</Tag></div>:<div className="flat-state"><Wallet size={28} strokeWidth={1.4}/><h3>Sin posiciones abiertas</h3><p>Saldo disponible en USDT.</p></div>}<div className="risk-strip"><span>Riesgo por entrada</span><strong>{o.policy.risk_pct}%</strong></div><div className="risk-strip"><span>Drawdown máximo</span><strong>{number(a.max_drawdown)}%</strong></div></section></div>
          </>}
          {view==='scanner'&&<section className="panel"><div className="scanner-toolbar"><div className="search"><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar BTC, ETH, SOL…" aria-label="Buscar mercado"/></div><div className="segmented">{[['all','Todos'],['analyzed','Analizados'],['ready','Setup válido']].map(([id,label])=><button key={id} className={filter===id?'selected':''} onClick={()=>setFilter(id)}>{label}</button>)}</div><span className="result-count">{marketRows.length} mercados</span></div><div className="table-scroll"><table><thead><tr><th>Mercado</th><th>Último precio</th><th>Cambio 24h</th><th>Volumen 24h</th><th>Spread</th><th>Filtros</th><th>Estado</th><th/></tr></thead><tbody>{marketRows.map(q=><tr key={q.symbol} onClick={()=>q.decision&&setSelected(q.decision)} className={q.decision?'clickable':''}><td><Asset symbol={q.symbol} base={q.base}/></td><td className="numeric">{price(q.last)}</td><td className={`numeric ${q.change_pct>=0?'positive':'negative'}`}>{pct(q.change_pct)}</td><td className="numeric">{volume(q.volume_usdt)}</td><td className="numeric">{q.bid>0&&q.ask>=q.bid?`${number((q.ask/q.bid-1)*100,3)}%`:'—'}</td><td>{q.decision?<Score value={q.decision.score}/>:<span className="muted">Sin análisis</span>}</td><td><Tag tone={q.decision?.eligible?'green':''}>{q.decision?.eligible?'SETUP':q.decision?'OBSERVANDO':'UNIVERSO'}</Tag></td><td>{q.decision&&<ArrowUpRight size={16}/>}</td></tr>)}</tbody></table>{!marketRows.length&&<Empty title="No hay coincidencias"/>}</div><div className="table-foot">El universo se descubre cada 6h. Cotizaciones REST cada ~15s; no es HFT. Los candidatos se analizan cada ~60s.</div></section>}
          {view==='portfolio'&&<><section className="stats-grid"><Stat label="Patrimonio" value={money(a.equity)} sub="Capital paper valorado a mercado" icon={Wallet}/><Stat label="Disponible en USDT" value={money(a.cash)} sub="Sin crédito ni apalancamiento" icon={ShieldCheck}/><Stat label="PnL abierto" value={money(a.unrealized,4)} sub="Incluye la comisión de entrada" icon={Activity}/><Stat label="Comisiones acumuladas" value={money(a.fees,4)} sub="Entradas y salidas efectivamente simuladas" icon={ListFilter}/></section><section className="panel"><div className="panel-head"><h2>Posiciones abiertas</h2><Tag>{o.positions.length} / 1</Tag></div>{o.positions.length?<div className="position-cards">{o.positions.map(p=><article className="position-card" key={p.id}><Asset symbol={p.symbol}/><div className="position-metrics">{[['Entrada',price(p.entry)],['Último bid',price(p.mark)],['Stop actual',price(p.stop)],['Objetivo',price(p.target)],['Cantidad',number(p.quantity,8)],['Apertura',date(p.opened_at)]].map(([l,v])=><div key={l}><small>{l}</small><strong>{v}</strong></div>)}</div>{!!p.dust&&<div className="alert">Residual no negociable. Conservado y valorado, sin venta ficticia.</div>}</article>)}</div>:<Empty title="Sin posiciones abiertas">Las entradas aparecerán cuando cumplan todos los filtros y el tamaño mínimo del exchange.</Empty>}</section><section className="panel spaced"><div className="panel-head"><h2>Historial de operaciones</h2><span className="muted">Máximo 100 recientes</span></div><TradeTable rows={data.activity.trades}/></section></>}
          {view==='decisions'&&<section className="panel"><div className="panel-head"><div><h2>Diario de decisiones</h2><p>Una decisión por moneda y vela. Las reevaluaciones no duplican órdenes.</p></div><Tag>Últimas 100</Tag></div><div className="table-scroll"><table><thead><tr><th>Hora</th><th>Mercado</th><th>Resultado</th><th>Score</th><th>Motivo</th></tr></thead><tbody>{data.activity.decisions.map(d=><tr key={d.id} className="clickable" onClick={()=>setSelected({...d.details,symbol:d.symbol})}><td className="muted nowrap">{date(d.at)}</td><td><Asset symbol={d.symbol}/></td><td><Tag tone={d.status==='ENTERED'?'green':d.status==='REJECTED'?'amber':''}>{names[d.status]||d.status}</Tag></td><td><Score value={d.score}/></td><td className="reason-text">{d.reason}</td></tr>)}</tbody></table>{!data.activity.decisions.length&&<Empty/>}</div></section>}
          {view==='strategy'&&<><div className="strategy-hero panel"><span className="strategy-icon"><Zap size={30}/></span><div><Tag>Spot · Paper</Tag><h2>Momentum intradía</h2><p>Impulso, consolidación y ruptura en velas cerradas de 5 minutos.</p></div></div><div className="rules-grid">{[
            ['01','Descubrir','Pares activos spot USDT de Binance. Se excluyen monedas estables conocidas y tokens apalancados. El universo no es una recomendación.'],
            ['02','Filtrar','Volumen de 24h ≥ $10M, spread ≤ 0,12% y cotizaciones frescas. Hasta 40 candidatos con actividad para análisis de velas.'],
            ['03','Confirmar','Impulso de 0,5–6%, consolidación de 3 velas y ruptura cerrada de 5m. Volumen ≥ 1,5× y compras agresoras ≥ 55%.'],
            ['04','Dimensionar','Riesgo objetivo de 0,5%, exposición máxima del 30% y una posición. Si el mínimo de Binance excede el presupuesto, no se opera.'],
            ['05','Gestionar','Stop por estructura/ATR (0,8–3%), objetivo 2R, seguimiento al alcanzar 1R y salida temporal a los 90 minutos.'],
            ['06','Medir','Fees del 0,1% por lado y slippage del 0,05% sobre bid/ask. Pérdida diaria del 3% o drawdown del 10% bloquean nuevas entradas.'],
          ].map(([n,title,text])=><article className="rule-card" key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}</div><div className="research-note"><CircleHelp size={22}/><div><h3>Investigación, no rentabilidad verificada</h3><p>No hay backtest fuera de muestra de esta combinación de reglas. El score mide filtros cumplidos, no la probabilidad de ganar. El simulador usa cotizaciones observadas cada ~15s: puede perder movimientos intraintervalo y no reproduce colas de órdenes ni todas las condiciones del exchange. La referencia BTC es fraccional, no una cartera ejecutable. Las comisiones reales pueden diferir. Estos límites de riesgo son objetivos, no garantías frente a gaps.</p></div></div></>}
          {o.scan_error&&<div className="alert spaced"><AlertTriangle size={17}/>{o.scan_error.error}</div>}
          <footer><span><span className="live-dot"/> Binance · Cuenta paper</span><span>TRADEMERC · Actualizado {time(o.at)}</span></footer>
        </>}
      </main>
    </div>
    {selected&&<div className="modal-backdrop" onClick={()=>setSelected(null)}><section role="dialog" aria-modal="true" aria-labelledby="detail-title" className="modal" onClick={e=>e.stopPropagation()}><div className="panel-head"><div><span className="eyebrow muted">ANÁLISIS DE OPORTUNIDAD</span><h2 id="detail-title">{selected.symbol}</h2></div><button autoFocus className="icon-button" aria-label="Cerrar detalle" onClick={()=>setSelected(null)}><X size={20}/></button></div><div className="detail-score"><Score value={selected.score}/><Tag tone={selected.eligible?'green':'amber'}>{selected.eligible?'CONFIGURACIÓN VÁLIDA':'NO CUMPLE TODOS LOS FILTROS'}</Tag></div><div className="check-grid">{Object.entries(selected.checks||{}).map(([key,value])=><div key={key}><span className={value?'positive':'muted'}>{value?<Check size={16}/>:<X size={16}/>}</span><span>{({liquidity:'Liquidez',spread:'Spread',impulse:'Impulso',consolidation:'Consolidación',breakout:'Ruptura',volume:'Expansión de volumen',buy_pressure:'Presión compradora',trend:'Tendencia',risk:'Stop válido',costs:'Costes'})[key]||key}</span></div>)}</div><div className="detail-data">{[['Precio de señal',price(selected.price)],['Volumen relativo',`${number(selected.volume_ratio)}×`],['Compras agresoras',`${number(selected.taker_ratio*100)}%`],['Stop inicial',`${number(selected.stop_pct)}%`],['Objetivo',`${number(selected.target_pct)}%`],['Vela UTC',selected.candle_at?new Date(selected.candle_at).toISOString().slice(0,16).replace('T',' '):'—']].map(([k,v])=><div key={k}><small>{k}</small><strong>{v}</strong></div>)}</div><p className="modal-note">Una configuración válida puede descartarse por capital, enfriamiento, precio o límites de riesgo. No equivale a una orden ni a una ganancia esperada.</p></section></div>}
  </div>;
}
function Score({value}) {return <span className="score"><span className="score-bar"><i style={{width:`${value}%`}}/></span><b>{value}</b></span>;}
function OpportunityTable({rows,onSelect}) {return <div className="table-scroll"><table><thead><tr><th>Mercado</th><th>Precio</th><th>Volumen rel.</th><th>Filtros</th><th/></tr></thead><tbody>{rows.map(r=><tr key={r.symbol} className="clickable" onClick={()=>onSelect(r)}><td><Asset symbol={r.symbol} base={r.base}/></td><td className="numeric">{price(r.price)}</td><td className="numeric">{number(r.volume_ratio)}×</td><td><Score value={r.score}/></td><td><ArrowUpRight size={16}/></td></tr>)}</tbody></table>{!rows.length&&<Empty/>}</div>;}
function TradeTable({rows}) {return <div className="table-scroll"><table><thead><tr><th>Activo</th><th>Estado</th><th>Entrada</th><th>Salida</th><th>PnL neto</th><th>Motivo</th><th>Hora</th></tr></thead><tbody>{rows.map(p=><tr key={p.id}><td><Asset symbol={p.symbol}/></td><td><Tag tone={p.status==='OPEN'?'green':''}>{p.status==='OPEN'?'ABIERTA':'CERRADA'}</Tag></td><td className="numeric">{price(p.entry)}</td><td className="numeric">{price(p.exit_price)}</td><td className={`numeric ${p.pnl>=0?'positive':'negative'}`}>{money(p.pnl,4)}</td><td className="muted">{p.exit_reason||'—'}</td><td className="muted nowrap">{date(p.closed_at||p.opened_at)}</td></tr>)}</tbody></table>{!rows.length&&<Empty title="Todavía no se han abierto operaciones"/>}</div>;}

createRoot(document.getElementById('root')).render(<App/>);
