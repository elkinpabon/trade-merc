import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from worker.bot_runner import run_bot_loop


if __name__ == '__main__':
    if not run_bot_loop(create_app(), max_cycles=1):
        raise SystemExit('The paper-trading cycle did not complete with full coverage.')
