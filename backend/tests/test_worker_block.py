import subprocess
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from scripts.run_worker_block import run_slot


class WorkerBlockTestCase(unittest.TestCase):
    def test_timed_out_cycle_is_retried(self):
        completed = Mock(returncode=0)
        with patch('scripts.run_worker_block.subprocess.run', side_effect=[subprocess.TimeoutExpired('worker', 10), completed]) as run, \
                patch('scripts.run_worker_block.time.sleep') as sleep:
            result = run_slot(datetime(2026, 9, 7, 2, 0), timeout_seconds=10)

        self.assertTrue(result)
        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(15)


if __name__ == '__main__':
    unittest.main()
