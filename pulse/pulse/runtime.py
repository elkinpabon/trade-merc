import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .execution import PaperEngine
from .market import Market
from .store import now_ms
from .strategy import evaluate, POLICY, VERSION

log = logging.getLogger('pulse')


class Runtime:
    def __init__(self, store):
        self.store = store
        self.market = Market()
        self.engine = PaperEngine(store)
        self.stop = threading.Event()
        self.threads = []

    def start(self):
        self.store.initialize(POLICY)
        stored_version = self.store.get('strategy_version')
        if stored_version and stored_version != VERSION:
            raise RuntimeError('Strategy version mismatch: use a new experiment database')
        self.store.set('strategy_version', VERSION)
        self.store.set('boot', {'at': now_ms()})
        for name, target in [('pulse-prices', self.prices), ('pulse-scanner', self.scanner)]:
            t = threading.Thread(target=target, name=name, daemon=True)
            self.threads.append(t)
            t.start()

    def shutdown(self):
        self.stop.set()
        for t in self.threads:
            t.join(timeout=20)

    def prices(self):
        while not self.stop.is_set():
            started = time.monotonic()
            try:
                if now_ms() - self.market.universe_at > 6 * 3600_000:
                    self.store.set('universe', self.market.discover())
                self.market.refresh()
                quotes, rules = self.market.snapshot()
                result = self.engine.monitor(quotes, rules)
                self.store.set('monitor', {**result, 'status': 'OK', 'error': None})
                self.store.set('market', {'at': now_ms(), 'rows': sorted(quotes.values(), key=lambda q: -q.get('volume_usdt', 0))})
            except Exception as exc:
                log.exception('Price monitor failed')
                self.store.set('monitor', {'at': now_ms(), 'status': 'ERROR', 'error': str(exc)[:500]})
            self.stop.wait(max(1, 15 - (time.monotonic()-started)))

    def scanner(self):
        self.stop.wait(5)
        while not self.stop.is_set():
            start = now_ms()
            try:
                candidates, liquid = self.market.candidates()
                if not candidates:
                    raise RuntimeError('Sin cotizaciones frescas para analizar')
                results, errors = [], []
                with ThreadPoolExecutor(max_workers=4) as pool:
                    futures = {pool.submit(self.market.candles, q['symbol']): q for q in candidates}
                    for future in as_completed(futures):
                        q = futures[future]
                        try:
                            decision = evaluate(future.result(), q, now_ms())
                            results.append({'symbol': q['symbol'], 'base': q['base'], **decision,
                                            'volume_usdt': q['volume_usdt'], 'change_pct': q['change_pct']})
                        except Exception as exc:
                            errors.append({'symbol': q['symbol'], 'error': str(exc)[:200]})
                results.sort(key=lambda d: (-int(d['eligible']), -d['score'], -d['volume_ratio'], d['symbol']))
                quotes, rules = self.market.snapshot()
                for decision in results:
                    symbol = decision['symbol']
                    decision['execution'] = self.engine.enter(symbol, decision, quotes.get(symbol, {}), rules[symbol])
                finished = now_ms()
                self.store.set('scan', {'started_at': start, 'at': finished,
                                       'duration_ms': finished-start, 'liquid_markets': liquid,
                                       'attempted': len(candidates), 'analyzed': len(results),
                                       'setups': sum(r['eligible'] for r in results),
                                       'errors': errors, 'status': 'PARTIAL' if errors else 'OK', 'rows': results})
            except Exception as exc:
                log.exception('Scanner failed')
                self.store.set('scan_error', {'at': now_ms(), 'error': str(exc)[:500]})
            self.stop.wait(max(1, 60 - (now_ms()-start)/1000))
