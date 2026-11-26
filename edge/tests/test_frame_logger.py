"""frame_logger.FrameLogger 단위 테스트.

실행: cd edge && python -m unittest tests/test_frame_logger.py
"""
import csv
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frame_logger import FIELDS, FrameLogger, new_log_path  # noqa: E402


class FrameLoggerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_disabled_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('LOG_FRAMES', None)
            fl = FrameLogger(log_dir=self.tmp.name)
        self.assertFalse(fl.enabled)
        fl.log({'ts': 1.0, 'owner_seen': True, 'phone_seen': False, 'person_count': 1, 'state': 'PRESENT'})
        fl.close()
        self.assertEqual(os.listdir(self.tmp.name), [])

    def test_env_on_writes_header_and_rows(self):
        with mock.patch.dict(os.environ, {'LOG_FRAMES': '1'}):
            fl = FrameLogger(log_dir=self.tmp.name)
        self.assertRegex(fl.path.name, r'^edge_\d{8}_\d{4}\.csv$')
        fl.log({'ts': 1700000000.12345, 'owner_seen': True, 'phone_seen': False, 'person_count': 2, 'state': 'PRESENT'})
        fl.log({'ts': 1700000000.2, 'owner_seen': False, 'phone_seen': True, 'person_count': 0, 'state': 'DISTRACTED'})
        fl.close()
        fl.close()  # 두 번 불러도 안전 (atexit)
        with open(fl.path, newline='', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        self.assertEqual(tuple(rows[0]), FIELDS)
        self.assertEqual(rows[1], ['1700000000.123', '1', '0', '2', 'PRESENT'])
        self.assertEqual(rows[2], ['1700000000.200', '0', '1', '0', 'DISTRACTED'])
        self.assertEqual(fl.rows, 2)

    def test_same_minute_does_not_overwrite(self):
        a = new_log_path('edge', self.tmp.name)
        a.write_text('x')
        b = new_log_path('edge', self.tmp.name)
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()
