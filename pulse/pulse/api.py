import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func

from .store import Store, Account, Position, Decision, Snapshot, serialize, now_ms
from .runtime import Runtime
from .strategy import POLICY, VERSION


@asynccontextmanager
async def lifespan(app):
    url = os.environ.get('PULSE_DATABASE_URL')
    if not url:
        raise RuntimeError('PULSE_DATABASE_URL required: no fallback to existing bots')
    store = Store(url)
    store.initialize(POLICY)
    app.state.store = store
    runtime = Runtime(store)
    app.state.runtime = runtime
    runtime.start()
    yield
    runtime.shutdown()
    store.engine.dispose()


app = FastAPI(title='TRADEMERC Mercado', lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get('/api/overview')
def overview():
    store = app.state.store
    timestamp = now_ms()
    monitor = store.get('monitor', {})
    scan = store.get('scan', {})
    scan_error = store.get('scan_error', {})
    with store.Session() as s:
        a = s.get(Account, 1)
        positions = s.scalars(select(Position).where(Position.status == 'OPEN')).all()
        closed = s.scalars(select(Position).where(Position.status == 'CLOSED')).all()
        snapshots = s.scalars(select(Snapshot).order_by(Snapshot.id.desc()).limit(10000)).all()[::-1]
        equity = float(a.cash) + sum(float(p.quantity*p.mark) for p in positions)
        realized = sum(float(p.pnl) for p in closed)
        wins = [p for p in closed if p.pnl > 0]
        profit = sum(float(p.pnl) for p in wins)
        loss = -sum(float(p.pnl) for p in closed if p.pnl < 0)
        fees = sum(float(p.entry_fee) + float(p.exit_fee or 0) for p in positions + closed)
        last = snapshots[-1] if snapshots else None
        healthy = (monitor.get('status') == 'OK' and monitor.get('position_quotes_fresh', False)
                   and timestamp-monitor.get('at', 0) < 60_000 and timestamp-scan.get('at', 0) < 180_000
                   and scan.get('status') == 'OK' and scan_error.get('at', 0) <= scan.get('at', 0))
        # Bucket by 5 minutes for a compact chart; include latest point.
        points = {p.at // 300_000: serialize(p) for p in snapshots}
        if last:
            points[last.at // 300_000] = serialize(last)
        return {'at': timestamp, 'name': 'TRADEMERC', 'mode': 'PAPER', 'version': VERSION,
                'health': 'ONLINE' if healthy else 'WARMING' if not scan else 'DEGRADED',
                'account': {'initial': float(a.initial_cash), 'cash': float(a.cash), 'equity': equity,
                            'return_pct': (equity/float(a.initial_cash)-1)*100,
                            'realized': realized, 'unrealized': equity-float(a.initial_cash)-realized,
                            'fees': fees, 'peak': float(a.peak),
                            'drawdown': (float(a.peak)-equity)/float(a.peak)*100,
                            'max_drawdown': float(s.scalar(select(func.max(Snapshot.drawdown))) or 0),
                            'started_at': a.started_at, 'trades': len(closed), 'wins': len(wins),
                            'profit_factor': profit/loss if loss else None,
                            'benchmark': float(last.benchmark) if last and last.benchmark is not None else None},
                'positions': [serialize(p) for p in positions],
                'curve': list(points.values()), 'policy': POLICY.__dict__,
                'universe': store.get('universe', {}),
                'scan': {k: v for k, v in scan.items() if k != 'rows'},
                'scan_error': scan_error if scan_error.get('at', 0) > scan.get('at', 0) else None,
                'monitor': monitor}


@app.get('/api/opportunities')
def opportunities():
    return app.state.store.get('scan', {'rows': [], 'errors': []})


@app.get('/api/market')
def market():
    return app.state.store.get('market', {'rows': []})


@app.get('/api/activity')
def activity():
    with app.state.store.Session() as s:
        decisions = s.scalars(select(Decision).order_by(Decision.id.desc()).limit(100)).all()
        trades = s.scalars(select(Position).order_by(Position.id.desc()).limit(100)).all()
        return {'decisions': [{**serialize(d), 'details': json.loads(d.details)} for d in decisions],
                'trades': [serialize(p) for p in trades]}


@app.get('/api/health')
def health():
    data = overview()
    return {'status': data['health'], 'mode': 'PAPER', 'at': data['at'],
            'monitor': data['monitor'], 'scan': data['scan']}


DIST = Path(__file__).resolve().parents[1] / 'web' / 'dist'
if (DIST / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/')
def index():
    if not (DIST / 'index.html').exists():
        raise HTTPException(503, 'Frontend not built')
    return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
