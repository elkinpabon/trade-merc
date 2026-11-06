import json
import os
import hmac
import hashlib
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, func

from .store import Store, Account, Position, Decision, Snapshot, serialize, now_ms
from .runtime import Runtime
from .strategy import POLICY, VERSION


@asynccontextmanager
async def lifespan(app):
    if os.environ.get('PULSE_COOKIE_SECURE', 'true').lower() != 'true':
        raise RuntimeError('PULSE_COOKIE_SECURE must be true; serve the app behind HTTPS')
    if not os.environ.get('PULSE_LOGIN_PIN_HASH') or len(os.environ.get('PULSE_SESSION_SECRET', '')) < 32:
        raise RuntimeError('PULSE authentication secrets must be configured before starting')
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
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[
    '212-56-34-67.sslip.io', 'localhost', '127.0.0.1', 'testserver',
])
LOGIN_NAME = os.environ.get('PULSE_LOGIN_USER', 'elkinpabon')
COOKIE_SECURE = os.environ.get('PULSE_COOKIE_SECURE', 'true').lower() == 'true'
LOGIN_ATTEMPTS = {}
LOGIN_LOCK = threading.Lock()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    pin: str = Field(min_length=1, max_length=128)


def session_serializer():
    secret = os.environ.get('PULSE_SESSION_SECRET')
    if not secret or len(secret) < 32:
        raise HTTPException(503, 'Autenticación no configurada')
    return URLSafeTimedSerializer(secret, salt='trademerc-session-v1')


def authenticated(request: Request):
    token = request.cookies.get('trademerc_session')
    if not token:
        return False
    try:
        payload = session_serializer().loads(token, max_age=12 * 60 * 60)
        return hmac.compare_digest(str(payload.get('sub', '')), LOGIN_NAME)
    except (BadSignature, SignatureExpired, HTTPException):
        return False


def pin_matches(pin):
    """Verify a salted PBKDF2 PIN hash; never keep plaintext PIN in service config."""
    try:
        algorithm, iterations, salt, expected = os.environ['PULSE_LOGIN_PIN_HASH'].split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', pin.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (KeyError, ValueError, TypeError):
        return False


def require_session(request: Request):
    if not authenticated(request):
        raise HTTPException(401, 'Inicia sesión para continuar')


@app.get('/api/auth/status')
def auth_status(request: Request):
    return {'authenticated': authenticated(request)}


@app.post('/api/auth/login')
def login(payload: LoginRequest, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != f"{request.url.scheme}://{request.headers.get('host', '')}":
        raise HTTPException(403, 'Origen no permitido')
    username = payload.username.strip()
    pin = payload.pin.strip()
    client = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    with LOGIN_LOCK:
        times = [at for at in LOGIN_ATTEMPTS.get(client, []) if now - at < 600]
        if len(times) >= 6:
            raise HTTPException(429, 'Demasiados intentos; espera unos minutos')
        times.append(now)
        LOGIN_ATTEMPTS[client] = times
    if not os.environ.get('PULSE_LOGIN_PIN_HASH'):
        raise HTTPException(503, 'Autenticación no configurada')
    if not (hmac.compare_digest(username, LOGIN_NAME) and pin_matches(pin)):
        raise HTTPException(401, 'Usuario o PIN incorrectos')
    with LOGIN_LOCK:
        LOGIN_ATTEMPTS.pop(client, None)
    token = session_serializer().dumps({'sub': LOGIN_NAME})
    response = JSONResponse({'authenticated': True, 'expires_in_seconds': 43200})
    response.set_cookie('trademerc_session', token, max_age=43200, httponly=True,
                        secure=COOKIE_SECURE, samesite='strict', path='/')
    return response


@app.post('/api/auth/logout')
def logout():
    response = JSONResponse({'authenticated': False})
    response.delete_cookie('trademerc_session', path='/', httponly=True,
                            secure=COOKIE_SECURE, samesite='strict')
    return response


@app.get('/api/overview')
def overview(request: Request):
    require_session(request)
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
def opportunities(request: Request):
    require_session(request)
    return app.state.store.get('scan', {'rows': [], 'errors': []})


@app.get('/api/market')
def market(request: Request):
    require_session(request)
    return app.state.store.get('market', {'rows': []})


@app.get('/api/activity')
def activity(request: Request):
    require_session(request)
    with app.state.store.Session() as s:
        decisions = s.scalars(select(Decision).order_by(Decision.id.desc()).limit(100)).all()
        trades = s.scalars(select(Position).order_by(Position.id.desc()).limit(100)).all()
        return {'decisions': [{**serialize(d), 'details': json.loads(d.details)} for d in decisions],
                'trades': [serialize(p) for p in trades]}


@app.get('/api/health')
def health(request: Request):
    require_session(request)
    data = overview(request)
    return {'status': data['health'], 'mode': 'PAPER', 'at': data['at'],
            'monitor': data['monitor'], 'scan': data['scan']}


@app.get('/trademerc-bull.svg')
def bull_logo():
    logo = DIST / 'trademerc-bull.svg'
    if not logo.exists():
        raise HTTPException(404, 'Brand asset not found')
    return FileResponse(logo, media_type='image/svg+xml', headers={'Cache-Control': 'public, max-age=86400'})


DIST = Path(__file__).resolve().parents[1] / 'web' / 'dist'
if (DIST / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/')
def index(request: Request):
    if os.environ.get('PULSE_COOKIE_SECURE', 'true').lower() == 'true' and request.url.scheme != 'https':
        raise HTTPException(400, 'HTTPS requerido')
    if not (DIST / 'index.html').exists():
        raise HTTPException(503, 'Frontend not built')
    if not authenticated(request):
        return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
    return FileResponse(DIST / 'index.html', headers={'Cache-Control': 'no-cache'})
