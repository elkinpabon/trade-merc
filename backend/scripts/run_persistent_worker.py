"""Persistent supervisor with a fresh Python process per aligned slot."""
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.run_worker_block import run_slot, slot_floor


if __name__ == '__main__':
    slot = slot_floor(datetime.utcnow())
    while True:
        print(f'VPS paper slot {slot.isoformat()}', flush=True)
        ok = run_slot(slot, 600)
        print(f'Slot result: {ok}', flush=True)
        slot = max(slot + timedelta(minutes=15), slot_floor(datetime.utcnow()) + timedelta(minutes=15))
        delay = (slot + timedelta(minutes=1) - datetime.utcnow()).total_seconds()
        time.sleep(max(0, delay))
