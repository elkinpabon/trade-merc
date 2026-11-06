import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Integer, String, Numeric, Text, BigInteger, create_engine, select, inspect, text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


class Account(Base):
    __tablename__ = 'pulse_account'
    id = Column(Integer, primary_key=True)
    cash = Column(Numeric(30, 12), nullable=False)
    initial_cash = Column(Numeric(30, 12), nullable=False)
    peak = Column(Numeric(30, 12), nullable=False)
    day_equity = Column(Numeric(30, 12), nullable=False)
    day = Column(String(10), nullable=False)
    started_at = Column(BigInteger, nullable=False)
    benchmark_price = Column(Numeric(30, 12))


class Position(Base):
    __tablename__ = 'pulse_positions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, index=True)
    quantity = Column(Numeric(30, 12), nullable=False)
    entry = Column(Numeric(30, 12), nullable=False)
    mark = Column(Numeric(30, 12), nullable=False)
    stop = Column(Numeric(30, 12), nullable=False)
    initial_stop = Column(Numeric(30, 12), nullable=False)
    target = Column(Numeric(30, 12), nullable=False)
    high = Column(Numeric(30, 12), nullable=False)
    entry_fee = Column(Numeric(30, 12), nullable=False)
    exit_price = Column(Numeric(30, 12))
    exit_fee = Column(Numeric(30, 12))
    pnl = Column(Numeric(30, 12))
    opened_at = Column(BigInteger, nullable=False)
    closed_at = Column(BigInteger)
    exit_reason = Column(String(100))
    dust = Column(Integer, nullable=False, default=0)
    signal_key = Column(String(100), nullable=False, unique=True)


class Decision(Base):
    __tablename__ = 'pulse_decisions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_key = Column(String(100), nullable=False, unique=True)
    symbol = Column(String(32), nullable=False)
    at = Column(BigInteger, nullable=False, index=True)
    status = Column(String(30), nullable=False)
    score = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    details = Column(Text, nullable=False)


class Snapshot(Base):
    __tablename__ = 'pulse_snapshots'
    id = Column(Integer, primary_key=True, autoincrement=True)
    at = Column(BigInteger, nullable=False, index=True)
    equity = Column(Numeric(30, 12), nullable=False)
    cash = Column(Numeric(30, 12), nullable=False)
    benchmark = Column(Numeric(30, 12))
    drawdown = Column(Numeric(12, 6), nullable=False)


class State(Base):
    __tablename__ = 'pulse_state'
    key = Column(String(40), primary_key=True)
    value = Column(Text().with_variant(MEDIUMTEXT(), 'mysql'), nullable=False)


def serialize(row):
    return {c.name: float(getattr(row, c.name)) if isinstance(getattr(row, c.name), Decimal)
            else getattr(row, c.name) for c in row.__table__.columns}


class Store:
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True, pool_recycle=240,
                                    **({'connect_args': {'check_same_thread': False}} if url.startswith('sqlite') else {}))
        self.Session = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        if self.engine.dialect.name == 'mysql':
            column = next(c for c in inspect(self.engine).get_columns('pulse_state') if c['name'] == 'value')
            if str(column['type']).upper().startswith('TEXT'):
                with self.engine.begin() as connection:
                    connection.execute(text('ALTER TABLE pulse_state MODIFY COLUMN value MEDIUMTEXT NOT NULL'))

    def initialize(self, policy):
        with self.Session.begin() as s:
            account = s.get(Account, 1)
            if not account:
                s.add(Account(id=1, cash=policy.initial_cash, initial_cash=policy.initial_cash,
                              peak=policy.initial_cash, day_equity=policy.initial_cash,
                              day=datetime.now(timezone.utc).date().isoformat(), started_at=now_ms()))
            if not s.get(State, 'policy'):
                s.add(State(key='policy', value=json.dumps(policy.__dict__)))
            elif json.loads(s.get(State, 'policy').value) != policy.__dict__:
                raise RuntimeError('La política cambió: utilizar una base nueva para otra prueba')

    def set(self, key, value):
        with self.Session.begin() as s:
            row = s.get(State, key)
            if row:
                row.value = json.dumps(value, allow_nan=False)
            else:
                s.add(State(key=key, value=json.dumps(value, allow_nan=False)))

    def get(self, key, default=None):
        with self.Session() as s:
            row = s.get(State, key)
            return json.loads(row.value) if row else default
