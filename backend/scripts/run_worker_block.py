import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta


SLOT_SECONDS = 15 * 60


def slot_floor(now: datetime) -> datetime:
    return now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)


def run_slot(slot: datetime, timeout_seconds: int) -> bool:
    environment = os.environ.copy()
    environment['WORKER_SLOT_AT'] = slot.isoformat()
    for attempt in range(2):
        try:
            result = subprocess.run(
                [sys.executable, 'backend/scripts/run_single_cycle.py'],
                env=environment, timeout=timeout_seconds, check=False,
            )
            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            print(f'Cycle slot {slot.isoformat()} timed out after {timeout_seconds}s.', flush=True)
        if attempt == 0:
            print(f'Cycle slot {slot.isoformat()} failed; retrying in 15 seconds.', flush=True)
            time.sleep(15)
    return False


def main():
    parser = argparse.ArgumentParser(description='Run aligned paper cycles from one GitHub runner')
    parser.add_argument('--cycles', type=int, default=8)
    parser.add_argument('--timeout-seconds', type=int, default=600)
    args = parser.parse_args()

    failures = []
    slot = slot_floor(datetime.utcnow())
    for index in range(max(1, args.cycles)):
        if index:
            slot += timedelta(seconds=SLOT_SECONDS)
            delay = (slot + timedelta(minutes=1) - datetime.utcnow()).total_seconds()
            if delay > 0:
                print(f'Waiting {int(delay)}s for slot {slot.isoformat()}.', flush=True)
                time.sleep(delay)
        print(f'Executing slot {slot.isoformat()} ({index + 1}/{args.cycles}).', flush=True)
        if not run_slot(slot, args.timeout_seconds):
            failures.append(slot.isoformat())

    if failures:
        raise SystemExit(f'Worker block finished with failed slots: {failures}')


if __name__ == '__main__':
    main()
