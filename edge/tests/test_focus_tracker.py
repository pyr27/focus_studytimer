"""presence.FocusTracker 상태머신 단위 테스트 (cv2 없이 실행 가능).

실행: cd edge && python -m unittest tests/test_focus_tracker.py
"""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _name in ('cv2', 'numpy', 'requests'):  # 무거운 의존성이 없으면 빈 모듈로 대체 (상태머신은 쓰지 않음)
    try:
        __import__(_name)
    except ImportError:
        sys.modules[_name] = types.ModuleType(_name)

from presence import IDLE, PRESENT, FocusTracker  # noqa: E402


def run(tracker, start, end, owner, phone=False, fps=10):
    """[start, end) 구간을 fps 로 흘리며 같은 검출 결과를 넣는다. 발생한 이벤트를 모아 돌려준다."""
    events, n = [], int(round((end - start) * fps))
    for k in range(n):
        events += tracker.step(start + k / fps, owner, phone)
    return events


class FocusTrackerSessionTest(unittest.TestCase):
    def setUp(self):
        self.t = FocusTracker(absent_sec=30, confirm_frames=3)

    def test_starts_idle_and_needs_confirm_frames(self):
        self.assertEqual(self.t.step(0.0, True), [])
        self.assertEqual(self.t.step(0.1, True), [])
        self.assertEqual(self.t.state, IDLE)
        ev = self.t.step(0.2, True)
        self.assertEqual(ev[0][0], 'session_start')
        self.assertEqual(self.t.state, PRESENT)

    def test_single_frame_misdetection_does_not_start_session(self):
        for k in range(20):
            self.t.step(k * 0.1, k % 2 == 0)  # 1프레임씩 깜빡임
        self.assertEqual(self.t.state, IDLE)

    def test_short_absence_counts_as_present(self):
        run(self.t, 0, 60, True)
        run(self.t, 60, 80, False)       # 20초 이탈 (< 30초)
        run(self.t, 80, 100, True)
        self.assertEqual(self.t.state, PRESENT)
        self.assertAlmostEqual(self.t.totals(100)['present_sec'], 100 - 0.2, delta=0.2)

    def test_absence_over_limit_ends_session_at_last_seen(self):
        run(self.t, 0, 60, True)          # 0.2s 에 세션 시작, 59.9s 마지막 인식
        ev = run(self.t, 60, 100, False)  # 30초 초과 이탈
        ends = [info for kind, info in ev if kind == 'session_end']
        self.assertEqual(len(ends), 1)
        s = ends[0]
        self.assertEqual(self.t.state, IDLE)
        self.assertAlmostEqual(s['present_sec'], 59.9 - 0.2, places=6)  # 이탈 후 30초는 포함하지 않음
        self.assertEqual(s['distracted_sec'], 0)
        self.assertAlmostEqual(s['focus_sec'], s['present_sec'])

    def test_new_session_after_end(self):
        run(self.t, 0, 10, True)
        run(self.t, 10, 50, False)
        ev = run(self.t, 50, 60, True)
        self.assertEqual([k for k, _ in ev], ['session_start'])
        self.assertEqual(len(self.t.sessions), 1)
        self.assertAlmostEqual(self.t.totals(60)['present_sec'], 60 - 50.2, places=6)


if __name__ == '__main__':
    unittest.main()
