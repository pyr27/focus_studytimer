"""V1 Edge 프레임 로그 (CSV) — 측정 정확도 검증용.

매 프레임 `ts, owner_seen, phone_seen, person_count, state` 를 logs/edge_YYYYMMDD_HHMM.csv 로 저장한다.
  ts           : time.time() (초, 소수 3자리). gt_logger.py 와 같은 시계 → 같은 PC 에서 두 로그를 시각으로 맞춘다
  owner_seen   : 이번 프레임에서 등록 사용자 얼굴 인식 (0/1, CONFIRM_FRAMES 적용 전 원시값)
  phone_seen   : 이번 프레임에서 cell phone 검출 (0/1)
  person_count : person 박스 수
  state        : IDLE / PRESENT / DISTRACTED

켜기: LOG_FRAMES=1 (기본 꺼짐). 저장 폴더: LOG_DIR (기본 logs, 실행 폴더 기준)
행 단위로 바로 기록하므로 Ctrl+C 로 끊어도 그때까지의 행은 남는다.
"""
import atexit
import csv
import os
from datetime import datetime
from pathlib import Path

FIELDS = ('ts', 'owner_seen', 'phone_seen', 'person_count', 'state')


def new_log_path(prefix, log_dir=None):
    """logs/<prefix>_YYYYMMDD_HHMM.csv — 같은 분에 이미 있으면 _1, _2 … 를 붙인다."""
    log_dir = Path(log_dir or os.environ.get('LOG_DIR', 'logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    stem = f'{prefix}_{datetime.now():%Y%m%d_%H%M}'
    path, n = log_dir / f'{stem}.csv', 0
    while path.exists():
        n += 1
        path = log_dir / f'{stem}_{n}.csv'
    return path


class FrameLogger:
    def __init__(self, enabled=None, log_dir=None):
        if enabled is None:
            enabled = os.environ.get('LOG_FRAMES', '0') == '1'
        self.enabled, self.path, self.rows = enabled, None, 0
        if not enabled:
            return
        self.path = new_log_path('edge', log_dir)
        self._f = open(self.path, 'w', newline='', encoding='utf-8', buffering=1)  # 줄 단위 flush
        self._w = csv.writer(self._f, lineterminator='\n')
        self._w.writerow(FIELDS)
        atexit.register(self.close)
        print(f'[FrameLog] {self.path}')

    def log(self, frame):
        """frame: PresenceDetection.last (dict) — ts, owner_seen, phone_seen, person_count, state."""
        if not self.enabled or self._f.closed:
            return
        self._w.writerow([f"{frame['ts']:.3f}", int(bool(frame['owner_seen'])), int(bool(frame['phone_seen'])),
                          int(frame['person_count']), frame['state']])
        self.rows += 1

    def close(self):
        if self.enabled and not self._f.closed:
            self._f.close()
            print(f'[FrameLog] {self.rows} rows -> {self.path}')
