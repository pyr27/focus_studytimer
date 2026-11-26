"""gt_logger 키 파싱 · CSV 기록 단위 테스트 (cv2 없이 실행 가능).

실행: cd edge && python -m unittest tests/test_gt_logger.py
"""
import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gt_logger import GtWriter, parse_key  # noqa: E402


class ParseKeyTest(unittest.TestCase):
    def test_keys(self):
        self.assertEqual(parse_key(ord('s')), 'study')
        self.assertEqual(parse_key(ord('P')), 'phone')
        self.assertEqual(parse_key(ord('a')), 'away')
        self.assertEqual(parse_key(ord('q')), 'quit')
        self.assertEqual(parse_key(27), 'quit')
        self.assertEqual(parse_key(ord('ㄴ')), 'study')  # 한글 입력 상태
        self.assertIsNone(parse_key(-1))
        self.assertIsNone(parse_key(ord('x')))


class GtWriterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'gt.csv')

    def rows(self):
        with open(self.path, newline='', encoding='utf-8') as f:
            return list(csv.reader(f))

    def test_change_interval_and_final_row(self):
        gw = GtWriter(self.path, interval=1.0)
        gw.tick(99.0)                 # 라벨 전에는 기록 안 함
        gw.set_label('study', 100.0)  # 즉시
        gw.tick(100.5)                # 간격 미달
        gw.tick(101.0)                # 1초 → 반복 기록
        gw.set_label('study', 101.2)  # 같은 라벨은 무시
        gw.set_label('phone', 101.5)  # 변경 즉시
        gw.set_label('bogus', 101.6)  # 알 수 없는 라벨 무시
        gw.close(102.25)              # 종료 시 마지막 행
        gw.close(103.0)               # 두 번 닫아도 안전
        self.assertEqual(self.rows(), [['ts', 'label'], ['100.000', 'study'], ['101.000', 'study'],
                                       ['101.500', 'phone'], ['102.250', 'phone']])

    def test_no_label_writes_header_only(self):
        GtWriter(self.path).close(5.0)
        self.assertEqual(self.rows(), [['ts', 'label']])


if __name__ == '__main__':
    unittest.main()
