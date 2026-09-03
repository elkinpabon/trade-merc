import os
import unittest
from unittest.mock import patch

os.environ['DATABASE_URL'] = 'sqlite://'

from app import create_app
from app.extensions import db
from app.models import BotConfig, RiskEvent, Signal
from app.services.risk_service import RiskService
from app.utils.helpers import generate_uuid, utc_now


class RiskServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()
        self.config = BotConfig(symbols='BTC/USDT', virtual_balance=100.0)
        db.session.add(self.config)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_audit_failure_does_not_block_risk_rejection(self):
        signal = Signal(
            id=generate_uuid(), bot_run_id='run', symbol='BTC/USDT', type='BUY',
            action='ENTER_LONG', price=100.0, status='PENDING', timestamp=utc_now(),
        )
        db.session.add(signal)
        db.session.commit()

        with patch.object(db.session, 'commit', side_effect=RuntimeError('legacy schema')):
            RiskService(self.config).log_risk_event('TEST', signal.symbol, 'audit failure')

        self.assertEqual(RiskEvent.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
